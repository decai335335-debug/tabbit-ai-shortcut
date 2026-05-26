# 开发日志 (Changelog)

## [v4.1] - 2026-05-26

### 新增
- **支持第 2 个妙招（magic_2）**
  - 新增 `magic_2.png` 模板图片支持
  - 新增独立快捷键 `Ctrl + Shift + Z` 触发第 2 个妙招
  - 提取通用函数 `_trigger_magic_common`，支持复用扩展更多妙招

### 变更
- **热键调整**：第 2 个妙招的快捷键从 `Ctrl + Shift + C` 改为 `Ctrl + Shift + Z`，避免与其他软件冲突
- **代码重构**：
  - 原 `trigger_magic()` 拆分为 `trigger_magic_1()` / `trigger_magic_2()`
  - 原 `on_hotkey()` 拆分为 `on_hotkey_1()` / `on_hotkey_2()`
  - 通过 `_trigger_magic_common()` 统一核心逻辑，减少重复代码

### 快捷键映射

| 快捷键 | 功能 | 说明 |
|--------|------|------|
| `Ctrl + Shift + X` | 触发第 1 个妙招 | 原有功能保持不变 |
| `Ctrl + Shift + Z` | 触发第 2 个妙招 | 新增 |
| `Ctrl + Shift + Q` | 退出程序 | 原有功能保持不变 |

---

## [v4.0] - 2025-05-23

### 初始版本
- 基于 OpenCV 图像识别的屏幕自动点击器
- 支持 `Ctrl + Shift + 1` 触发单条妙招流程
- 添加调试截图保存到 `debug/` 文件夹
- 移除全局鼠标监听，避免阻塞系统
