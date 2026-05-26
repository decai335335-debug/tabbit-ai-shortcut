#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 妙招自动点击器 v4.0 - 安全简化版
功能：通过图像识别自动找到屏幕上的按钮并点击，支持热键触发。

原理：
1. 提前准备好按钮的截图（模板图片）
2. 运行时截取屏幕，用 OpenCV 在屏幕上寻找模板图片的位置
3. 找到后移动鼠标并点击
4. 通过 keyboard 库注册热键（Ctrl+Shift+X），按下即触发

注意：移除了全局鼠标监听，避免阻塞系统
"""

import os          # 文件路径、目录操作
import sys         # 系统相关（如 sys.exit 退出程序）
import time        # 时间控制（sleep 延时）
import ctypes      # 调用 Windows 底层 API（移动鼠标、模拟点击）
import logging     # 日志记录（把操作记录保存到文件）
import threading   # 多线程（让热键触发不阻塞主程序）
from datetime import datetime  # 获取当前时间（用于日志文件名）

import cv2         # OpenCV：计算机视觉库，用于图像匹配
import numpy as np  # NumPy：数值计算库，图像在内存中以 NumPy 数组形式存在
import keyboard    # keyboard：监听和发送键盘事件
from PIL import ImageGrab  # PIL：截图功能

# ============ 配置区域 ============
# __file__ 是当前脚本的完整路径，dirname 获取它所在的文件夹
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 创建 debug 文件夹（如果不存在），用于保存调试截图
# exist_ok=True 表示如果文件夹已存在，不报错
DEBUG_DIR = os.path.join(SCRIPT_DIR, "debug")
os.makedirs(DEBUG_DIR, exist_ok=True)

# 定义要识别的按钮模板图片路径
# key 是按钮的名字（代码里用），value 是图片文件路径
BUTTON_TEMPLATES = {
    "miaozhao": os.path.join(SCRIPT_DIR, "button_miaozhao.png"),  # 主按钮
    "magic_1": os.path.join(SCRIPT_DIR, "magic_1.png"),          # 子菜单按钮1
    "magic_2": os.path.join(SCRIPT_DIR, "magic_2.png"),          # 子菜单按钮2
}

# 图像匹配参数
CONFIDENCE = 0.06           # 匹配阈值（0-1），越高要求越严格。0.06 适合半透明按钮
SEARCH_TIMEOUT = 0.02       # 搜索超时时间（秒）
CLICK_DELAY = 0.01          # 点击前的等待时间
STEP_DELAY = 0.01           # 步骤之间的等待时间

# ============ Windows API 常量 ============
# ctypes.windll.user32 是 Windows 的用户界面库
user32 = ctypes.windll.user32

# mouse_event 函数的常量标志（Windows 系统定义）
MOUSEEVENTF_MOVE = 0x0001       # 移动鼠标
MOUSEEVENTF_LEFTDOWN = 0x0002   # 按下左键
MOUSEEVENTF_LEFTUP = 0x0004     # 松开左键
MOUSEEVENTF_ABSOLUTE = 0x8000   # 使用绝对坐标（0-65535 映射到全屏）

# 获取屏幕分辨率
SCREEN_WIDTH = user32.GetSystemMetrics(0)   # 0 = SM_CXSCREEN（屏幕宽度）
SCREEN_HEIGHT = user32.GetSystemMetrics(1)  # 1 = SM_CYSCREEN（屏幕高度）


def get_mouse_pos():
    """
    获取当前鼠标指针的屏幕坐标。
    
    返回:
        tuple: (x, y) 坐标
    """
    # 创建一个 POINT 结构体（Windows API 的坐标类型）
    pt = ctypes.wintypes.POINT()
    # GetCursorPos 把当前鼠标坐标写入 pt
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def move_mouse(x, y):
    """
    将鼠标移动到屏幕上的绝对坐标位置。
    
    Windows 的绝对坐标系是 0-65535，需要把像素坐标转换为这个范围。
    例如屏幕 1920x1080，要移动到 (960, 540)：
        abs_x = 960 * 65535 / 1920 = 32767
    """
    abs_x = int(x * 65535 / SCREEN_WIDTH)
    abs_y = int(y * 65535 / SCREEN_HEIGHT)
    # mouse_event 发送鼠标移动事件
    user32.mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, abs_x, abs_y, 0, 0)


# ============ 日志设置 ============
# 日志文件路径：脚本目录下的 operation_log.txt
log_file = os.path.join(SCRIPT_DIR, "operation_log.txt")

# basicConfig 配置日志系统
# level=logging.INFO：只记录 INFO 级别及以上的日志（DEBUG < INFO < WARNING < ERROR）
# format：日志格式，包含时间戳和消息
# handlers：同时输出到文件和控制台
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',  # asctime = 时间戳
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),  # 写入文件
        logging.StreamHandler(sys.stdout)                 # 同时打印到屏幕
    ]
)
logger = logging.getLogger(__name__)  # 获取 logger 实例

# ============ 全局状态变量 ============
# global 声明：这些变量在函数内被修改时需要声明
script_click_count = 0   # 统计本次执行点击了多少次
is_running = False       # 防止重复触发（正在执行时忽略新的热键）

# ============ 截图功能 ============
def take_screenshot():
    """
    截取整个屏幕。
    
    返回:
        PIL.Image: 屏幕截图对象
    """
    return ImageGrab.grab()


def save_debug_screenshot(name):
    """
    保存调试截图，文件名包含时间戳，避免覆盖。
    
    参数:
        name (str): 截图描述名（如 "01_start"）
    
    返回:
        str: 保存的文件路径
    """
    # datetime.now().strftime("%H%M%S") 格式化当前时间为 "时分钟秒"
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"debug_{name}_{timestamp}.png"
    filepath = os.path.join(DEBUG_DIR, filename)
    take_screenshot().save(filepath)
    logger.info(f"截图: {filename}")
    return filepath


# ============ 图像识别核心 ============
def find_button(template_path, confidence=CONFIDENCE, timeout=SEARCH_TIMEOUT):
    """
    在屏幕上寻找指定的按钮图片（模板匹配）。
    
    原理：
    1. 截取当前屏幕
    2. 读取模板图片
    3. 用 cv2.matchTemplate 在屏幕上滑动模板，计算相似度
    4. 找到相似度最高的位置，如果超过阈值就认为找到了
    
    参数:
        template_path (str): 模板图片的路径
        confidence (float): 匹配阈值，0-1 之间
        timeout (float): 最多搜索多少秒
    
    返回:
        tuple: (center_x, center_y) 按钮中心坐标，找不到返回 None
    """
    start_time = time.time()  # 记录开始时间
    attempt = 0
    
    # 在超时时间内循环尝试
    while time.time() - start_time < timeout:
        attempt += 1
        
        # 1. 截取屏幕
        screenshot = take_screenshot()
        # 把 PIL Image 转换为 NumPy 数组，并调整颜色通道顺序（RGB -> BGR，因为 OpenCV 用 BGR）
        screenshot_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # 2. 读取模板图片
        # 注意：cv2.imread 不支持中文路径，所以用 numpy.fromfile + cv2.imdecode
        try:
            file_bytes = np.fromfile(template_path, dtype=np.uint8)
            template = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.error(f"读取模板失败: {template_path}, 错误: {e}")
            return None
        
        # 如果模板读取失败（文件不存在或损坏）
        if template is None:
            logger.error(f"无法读取模板: {template_path}")
            return None
        
        # 3. 模板匹配
        # cv2.matchTemplate 会在 screenshot 上滑动 template，计算每个位置的相似度
        # cv2.TM_CCOEFF_NORMED 是一种匹配算法，输出范围 -1 到 1，越接近 1 越相似
        result = cv2.matchTemplate(screenshot_np, template, cv2.TM_CCOEFF_NORMED)
        
        # minMaxLoc 找出结果中的最小值、最大值及其位置
        # min_val: 最小相似度, max_val: 最大相似度
        # min_loc: 最小值位置, max_loc: 最大值位置
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # 4. 判断是否找到
        if max_val >= confidence:
            # 计算模板中心点坐标
            # template.shape 返回 (高度, 宽度, 通道数)，[:2] 取前两个
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2  # 左上角 x + 宽度的一半
            center_y = max_loc[1] + h // 2  # 左上角 y + 高度的一半
            logger.info(f"找到按钮: ({center_x}, {center_y}) 置信度: {max_val:.3f}")
            return (center_x, center_y)
        
        # 没找到，记录日志并等待后重试
        logger.info(f"尝试 {attempt}: 未找到 (置信度 {max_val:.3f} < {confidence})")
        time.sleep(0.1)
    
    # 超时未找到
    logger.error(f"超时 {timeout}s，未找到按钮")
    return None


# ============ 点击功能 ============
def safe_click(x, y, description=""):
    """
    安全地移动鼠标到指定位置并点击。
    
    参数:
        x, y: 屏幕坐标
        description: 点击描述（用于日志）
    """
    global script_click_count  # 声明使用全局变量
    
    logger.info(f"点击 {description}: ({x}, {y})")
    move_mouse(x, y)           # 移动鼠标
    time.sleep(CLICK_DELAY)    # 短暂等待，确保鼠标到位
    
    # 模拟鼠标按下和松开
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)  # 按住 50 毫秒（模拟真实点击）
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    
    script_click_count += 1    # 计数器加 1
    time.sleep(0.1)            # 点击后等待，给 UI 响应时间


# ============ 主流程 ============
def _trigger_magic_common(magic_key, magic_label):
    """
    触发"妙招"的通用流程：
    1. 找到"妙招"按钮并点击
    2. 等待菜单弹出
    3. 找到指定的妙招按钮并点击
    4. 恢复鼠标位置
    
    参数:
        magic_key: BUTTON_TEMPLATES 中的键名（如 "magic_1" 或 "magic_2"）
        magic_label: 日志中显示的名称（如 "第1个妙招" 或 "第2个妙招"）
    """
    global script_click_count, is_running
    
    # 如果正在执行中，忽略本次触发（防止重复执行）
    if is_running:
        logger.warning("正在执行中，忽略")
        return
    
    is_running = True          # 设置执行标志
    script_click_count = 0     # 重置点击计数
    
    try:
        logger.info("="*50)
        logger.info(f"开始执行 - {magic_label}")
        
        # 记录初始鼠标位置，执行完后恢复
        initial_pos = get_mouse_pos()
        save_debug_screenshot("01_start")
        
        # ===== 第 1 步：点击"妙招"按钮 =====
        # BUTTON_TEMPLATES["miaozhao"] 获取模板图片路径
        pos1 = find_button(BUTTON_TEMPLATES["miaozhao"])
        if not pos1:
            save_debug_screenshot("02_fail")
            return  # 找不到按钮，直接结束
        
        # pos1 是 (x, y) 元组，pos1[0] 是 x，pos1[1] 是 y
        safe_click(pos1[0], pos1[1], "妙招")
        
        # 等待菜单弹出
        logger.info(f"等待菜单 {STEP_DELAY}s...")
        time.sleep(STEP_DELAY)
        save_debug_screenshot("03_menu")
        
        # ===== 第 2 步：点击指定的妙招 =====
        pos2 = find_button(BUTTON_TEMPLATES[magic_key])
        if not pos2:
            save_debug_screenshot("04_fail")
            return
        
        safe_click(pos2[0], pos2[1], magic_label)
        
        # 完成，等待一下，恢复鼠标位置
        time.sleep(0.1)
        save_debug_screenshot("05_success")
        move_mouse(initial_pos[0], initial_pos[1])
        
        logger.info(f"完成! 点击次数: {script_click_count}")
        logger.info("="*50)
    
    except Exception as e:
        # 任何异常都不应该让程序崩溃，记录错误即可
        logger.error(f"出错: {e}")
    
    finally:
        # finally 块确保无论成功还是失败，都重置执行标志
        is_running = False


def trigger_magic_1():
    """触发第1个妙招（Ctrl+Shift+X）"""
    _trigger_magic_common("magic_1", "第1个妙招")


def trigger_magic_2():
    """触发第2个妙招（Ctrl+Shift+Z）"""
    _trigger_magic_common("magic_2", "第2个妙招")


def on_hotkey_1():
    """
    热键回调函数（第1个妙招）。
    
    当用户按下 Ctrl+Shift+X 时，keyboard 库会调用这个函数。
    为了不影响热键监听线程，用 threading.Thread 在新线程中执行实际的点击逻辑。
    daemon=True 表示这是守护线程，主程序退出时自动结束。
    """
    threading.Thread(target=trigger_magic_1, daemon=True).start()


def on_hotkey_2():
    """
    热键回调函数（第2个妙招）。
    
    当用户按下 Ctrl+Shift+Z 时，keyboard 库会调用这个函数。
    """
    threading.Thread(target=trigger_magic_2, daemon=True).start()


def main():
    """
    程序入口：初始化热键监听，等待用户触发。
    """
    print("="*50)
    print("AI 妙招自动点击器 v4.0 (安全版)")
    print("="*50)
    print(f"目录: {SCRIPT_DIR}")
    print()
    
    # 检查模板文件是否存在
    for name, path in BUTTON_TEMPLATES.items():
        status = "[OK]" if os.path.exists(path) else "[FAIL]"
        print(f"{status} {name}")
    print()
    
    print("Ctrl+Shift+X = 触发第1个妙招")
    print("Ctrl+Shift+Z = 触发第2个妙招")
    print("Ctrl+Shift+Q = 退出")
    print()
    print("等待快捷键...")
    
    # 注册热键
    # add_hotkey(热键组合, 回调函数)
    keyboard.add_hotkey('ctrl+shift+x', on_hotkey_1)
    keyboard.add_hotkey('ctrl+shift+z', on_hotkey_2)
    keyboard.add_hotkey('ctrl+shift+q', lambda: sys.exit(0))  # lambda 是匿名函数
    
    # wait() 阻塞当前线程，持续监听热键
    keyboard.wait()


if __name__ == "__main__":
    main()
