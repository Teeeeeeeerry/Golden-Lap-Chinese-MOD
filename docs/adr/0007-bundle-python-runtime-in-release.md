# 发布包内置独立 Python 运行环境

**Status:** accepted

此前，玩家要先自己装 Python 3.11 或更新版本（macOS 自带的通常是 3.9），安装器第一次运行时还要联网从 PyPI 下载依赖。不熟悉电脑的玩家大多卡在「装 Python」这一步；网络不好时，下载依赖也会失败。

决定：发布包自带一份独立的 Python 运行环境，安装器和还原脚本优先使用它，不再找系统 Python、不建虚拟环境，也不联网。
- 解释器用 python-build-standalone 的 install_only 构建（Python 3.12，与开发环境一致）。去掉图形界面（tkinter、IDLE、Tcl/Tk）、pip、头文件、手册等用不到的部分，只保留一个真实的可执行文件，不留符号链接，免得 zip 解压后失效。
- 依赖按目标架构取 PyPI 上的 wheel，直接按 wheel 规范解压进运行环境的 site-packages，不经过 pip。PyPI 上只有源码包的纯 Python 依赖（tpk_ar），取出其中的包目录。
- 解释器和每个依赖的下载地址、sha256 都锁定在 `packaging/runtime.lock.json`，由维护者运行脚本重新生成。构建时按 sha256 校验，下载内容缓存在仓库外，同样的锁定文件得到逐字节相同的发布包。
- 在仓库里直接运行脚本时（没有内置运行环境），仍按原方式查找系统 Python 并建虚拟环境，方便开发。
- 解除隔离属性必须在第一次运行内置 Python 之前完成，否则 Gatekeeper 会逐个拦截其中的二进制文件。

许可审查：CPython 为 PSF 许可，python-build-standalone 构建项目为 MPL-2.0，其余依赖均为 MIT、BSD 或 MIT-CMU，许可证随包附上（见 `packaging/THIRD-PARTY.md`）。`fmod_toolkit` 内含商业授权的 FMOD 引擎二进制，不随包分发；UnityPy 只在导出音频时才导入它，汉化不处理音频，已验证去掉它后构建和安装都照常工作。

**Considered Options:**
- **第一次运行时自动下载独立 Python 和依赖**（否决）：发布包虽小，但仍要联网，还多依赖一个外部下载源。
- **用 PyInstaller 打成单个可执行文件**（否决）：每次要在对应架构的机器上构建，体积不比内置运行环境小，还更难排查问题。
- **Apple 开发者签名并公证**（否决）：需要付费开发者账号；双击时的拦截改由一行安装命令绕开（见 #43）。

**Consequences:**
- 发布包从不到 1 MB 增大到每个架构约 40 MB。运行环境分芯片架构，发布包也按架构分开；先提供 Apple 芯片的包，Intel 包随后补上（#42）。
- 最低系统要求为 macOS 11，以内置运行时和依赖 wheel 的要求为准。
- 升级依赖要重新生成锁定文件；`requirements.txt` 仍用于开发环境，其中的 `fmod_toolkit` 只在开发环境安装。
