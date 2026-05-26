# AI 妙招自动点击器 (AI Trick Auto Clicker)

> 框选文字 → 按快捷键 → 自动触发妙招。一个轻量级的 Windows 屏幕自动化工具。

## 功能

- 支持多个妙招快捷键，自动完成两步点击：
  1. 找到并点击屏幕上的「妙招」按钮（展开菜单）
  2. 找到并点击菜单中对应的妙招
- 基于 OpenCV 图像识别，无需依赖任何浏览器或软件的 API
- 每一步执行后自动保存调试截图到 `debug/` 文件夹

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl + Shift + X` | 触发第 1 个妙招（magic_1） |
| `Ctrl + Shift + Z` | 触发第 2 个妙招（magic_2） |
| `Ctrl + Shift + Q` | 退出程序 |

## 依赖

```powershell
pip install opencv-python pillow numpy keyboard
```

## 使用方法

1. 确保依赖已安装
2. 框选需要处理的文字
3. 运行脚本：
   ```powershell
   python ai_button_hotkey_v4.py
   ```
4. 按对应快捷键触发妙招
5. 按 `Ctrl + Shift + Q` 退出

## 自定义模板图片

如需匹配不同的按钮图标或添加更多妙招：

1. 用截图工具截取按钮图标（**只截按钮本身，不要留白边**）
2. 保存为 PNG 格式到脚本目录
3. 修改脚本中的 `BUTTON_TEMPLATES` 字典：
   ```python
   BUTTON_TEMPLATES = {
       "miaozhao": os.path.join(SCRIPT_DIR, "button_miaozhao.png"),
       "magic_1": os.path.join(SCRIPT_DIR, "magic_1.png"),
       "magic_2": os.path.join(SCRIPT_DIR, "magic_2.png"),  # 新增
   }
   ```
4. 复制 `trigger_magic_2` 和 `on_hotkey_2` 的模式添加新的触发器和热键绑定

## 文件说明

```
.
├── ai_button_hotkey_v4.py   # 主脚本（安全简化版）
├── button_miaozhao.png     # 「妙招」按钮模板
├── magic_1.png             # 第 1 个妙招模板
├── magic_2.png             # 第 2 个妙招模板
├── CHANGELOG.md            # 开发日志
└── README.md
```

## 技术方案

| 组件 | 方案 |
|------|------|
| 图像识别 | OpenCV 模板匹配 (`cv2.matchTemplate`) |
| 鼠标移动 | Windows API `mouse_event(MOUSEEVENTF_ABSOLUTE)` |
| 鼠标点击 | Windows API `mouse_event(LEFTDOWN/LEFTUP)` |
| 快捷键 | `keyboard` 库 |
| 调试截图 | PIL `ImageGrab` |

## 注意事项

- 模板图片必须与目标按钮**外观完全一致**（大小、颜色、背景）
- 如果按钮位置或样式发生变化，需重新截图更新模板
- 只支持主显示器

## 许可证

MIT
