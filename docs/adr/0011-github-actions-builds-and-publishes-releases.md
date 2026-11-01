# 由 GitHub Actions 构建并发布 Release

**Status:** accepted

`scripts/release.py` 从解压后的文件读取内置 Python 的可执行位。在 Windows 上这个权限位可能丢失，打出的 macOS 发布包可能无法运行。维护者现在主要在 Windows 上工作，也不做 Mac 实机回归。

决定：打 `v<版本>` 标签后由 GitHub Actions 构建。macOS 运行器打 arm64 和 x86_64 两个包，Windows 运行器打 x64 包，全部成功后才自动公开为正式 Release。两个平台共用 `VERSION` 和同一个 Release。同一套工作流也在 macOS 和 Windows 上运行单元测试。

**Considered Options:**
- **`release.py` 改为从 tar 包取权限位，继续手动打包上传**（否决）：发布仍依赖人工操作，也不解决跨系统验证。
- **两个平台各发独立版本**（否决）：macOS 的一行安装命令依赖 `releases/latest/download/install.sh`，最新 Release 是 Windows 版时会 404。
- **先发 pre-release 或草稿，人工检查后再公开**（否决）：维护者选择打标签即发布，出问题再修。

**Consequences:**
- 打标签就是对外发布，打标签前要确认版本就绪。
- CI 没有游戏文件，只覆盖单元测试。平台层重构后，macOS 玩家会通过一行安装命令直接拿到未经实机验证的版本，这个风险已接受。
- 发布流程依赖 GitHub Actions，第一次要调通工作流。
