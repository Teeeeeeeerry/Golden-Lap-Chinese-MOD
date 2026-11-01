# 共用注入核心，平台层分包维护

**Status:** accepted

Windows 版和 macOS 版的游戏文件布局、Steam 位置、备份位置和打包方式都不同，但译文和注入逻辑相同。用同一套译文对 Windows 版做更新比对，四张字符串表全部无变化。

决定：`src/glzh` 只保留与平台无关的注入逻辑。`macos/glzh_macos/` 和 `windows/glzh_windows/` 各是一个 Python 包，放查找游戏、游戏文件布局、备份位置和运行前检查，并各有 `__main__.py`，把平台对象传给核心的命令行入口。启动脚本改为 `python -m glzh_macos …` 和 `python -m glzh_windows …`。核心里不判断 `sys.platform`，每个发布包只带自己的平台包。

**Considered Options:**
- **全部放在 `src/glzh`，`windows/` 只放启动脚本**（否决）：平台分支会散落在共用代码里，改 Windows 时容易碰到 macOS。
- **复制一份完整的注入代码到 `windows/`**（否决）：T21、T22 这类注入修复要改两遍、测两遍。
- **`glzh` 按 `sys.platform` 动态导入平台包**（否决）：启动脚本不用改，但要伪造平台才能跨系统测试平台层。

**Consequences:**
- 取代 spec 第 23 条“仅补一个 Windows 安装器”的设想，`steam.py`、`game.py` 里的 macOS 部分要搬到 `macos/glzh_macos/`。
- 开发时 `PYTHONPATH` 要同时包含 `src` 和对应的平台目录，单元测试在两个系统上都能导入两个平台包。
- catalog 的路径分隔符（macOS 用 `/`，Windows 用 `\`）属于核心逻辑，要在核心里同时支持。
