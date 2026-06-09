# GUI Agent Week 1

本项目主要实现 GUI 智能体看屏幕、识别文字、定位 UI 元素、控制鼠标键盘的基础模块。

## 功能

- 屏幕截图：`capture_screen()`
- OCR 文字识别：`run_ocr()`
- OCR 结果转统一元素格式：`UIElement`
- 文本定位：`find_text_element(keyword)`
- 桌面控制：点击、输入、滚动、拖拽
- 完整 demo：截图 -> OCR -> 找文本 -> 点击
- pytest 单元测试

## 项目结构

```text
gui_agent_week1/
├─ gui_agent/              # 核心功能模块
├─ manual_tests/           # 手动实验脚本
├─ tests/                  # 自动单元测试
├─ artifacts/              # 实验截图、JSON 日志、测试结果
├─ requirements.txt
└─ README.md
```

## 环境安装

建议使用 Python 3.11。

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install torch paddlepaddle-gpu paddleocr
```

更详细的环境说明见：

```text
GUI 智能体开发环境配置文档.pdf
```

## 运行手动实验

所有命令建议在项目根目录执行。

截图：

```powershell
python -m manual_tests.manual_capture --delay 5
```

OCR：

```powershell
python -m manual_tests.manual_ocr --delay 5
```

文本查找：

```powershell
python -m manual_tests.manual_find_text "Cheat Sheet" --delay 5
```

控制动作：

```powershell
python -m manual_tests.manual_control click --x 115 --y 600 --delay 5 
python -m manual_tests.manual_control type --text "hello" --delay 5 
python -m manual_tests.manual_control scroll --amount -500 --delay 5
python -m manual_tests.manual_control drag --start-x 700 --start-y 700 --end-x 1000 --end-y 1000 --delay 5
```

完整 find-and-click demo：

```powershell
python -m manual_tests.demo_find_and_click "Cheat Sheet" --click --delay 5 
```

实验结果保存在：

```text
artifacts/
```

## 运行自动测试

```powershell
python -m pytest -q
```

当前测试覆盖：

- 感知模块：截图、OCR、文本定位
- 控制模块：点击、输入、滚动、拖拽
- demo 流程：find-and-click dry-run