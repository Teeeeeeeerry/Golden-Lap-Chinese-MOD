# Golden Lap 简体中文汉化

给 Golden Lap 加上简体中文界面。支持 macOS 和 Windows 上的 Steam 版。

汉化在你的电脑上修改游戏文件。本仓库和发布包都不含游戏原始资源和字体，中文字形用的是游戏自带的思源黑体。

## 安装

### Windows

需要 Windows 10 或更新版本（64 位），不用安装 Python。

1. 从 [Releases](https://github.com/Teeeeeeeerry/Golden-Lap-Chinese-MOD/releases) 下载文件名以 `windows-x86_64.zip` 结尾的发布包。
2. 退出游戏，完整解压后双击 `install.bat`。
3. 启动游戏，进入设置 → 语言，选择「简体中文」。

如果弹出「Windows 已保护你的电脑」，点「更多信息」→「仍要运行」。详细说明见 [Windows 玩家说明](docs/release-README-windows.md)。

### macOS

需要 macOS 11 或更新版本，不用安装 Python。打开「终端」，粘贴下面这一行，按回车：

```bash
/bin/bash -c "$(curl -fsSL https://github.com/Teeeeeeeerry/Golden-Lap-Chinese-MOD/releases/latest/download/install.sh)"
```

它会判断你的 Mac 是 Apple 芯片还是 Intel，下载最新的发布包并校验 sha256，然后找到 Steam 中的游戏，备份原始文件并注入汉化。

装好后启动游戏，进入设置 → 语言，选择「简体中文」。这个选项占用的是土耳其语的位置，所以安装后不能再用土耳其语界面。

不想用终端的话，可以从 [Releases](https://github.com/Teeeeeeeerry/Golden-Lap-Chinese-MOD/releases) 下载压缩包，步骤见[玩家说明](docs/release-README.md)。游戏装在其他位置时的处理方法也在里面。

## 游戏更新后

游戏更新或在 Steam 中验证文件完整性后，汉化会被覆盖。再运行一次安装即可（macOS 用安装命令，Windows 双击 `install.bat`），升级汉化也一样，原有备份会沿用。

## 卸载

Windows：退出游戏后双击发布包里的 `restore.bat`。备份在 `%LOCALAPPDATA%\GoldenLapZHackup`。

macOS：

```bash
/bin/bash -c "$(curl -fsSL https://github.com/Teeeeeeeerry/Golden-Lap-Chinese-MOD/releases/latest/download/install.sh)" glzh restore
```

被改动的文件会从备份恢复，土耳其语选项也会回来。备份在 `~/Library/Application Support/GoldenLapZH/backup`，确认不再需要后可以删除整个 `GoldenLapZH` 文件夹。

## 翻译范围

- 菜单、事件、内容说明和比赛界面都已汉化。
- 车队名、赛道名、车手名保留英文。
- 目前的译文全部是机翻初稿，欢迎提交 issue 或 PR 校对。

## 开发

需要 Python 3.11 或更新版本。部分测试要读取本机安装的游戏文件，全量测试大约 25 分钟。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

常用命令：

| 命令 | 作用 |
| --- | --- |
| `PYTHONPATH=src:macos .venv/bin/python -m glzh_macos validate` | 校验译文 |
| `PYTHONPATH=src:macos .venv/bin/python -m glzh_macos diff [--write]` | 游戏更新后比对英文原文的变化 |
| `PYTHONPATH=src:macos .venv/bin/python -m glzh_macos build <目录>` | 构建到仓库外的目录，不改动游戏 |

Windows 上用 `windows` 代替 `macos`、`glzh_windows` 代替 `glzh_macos`，`PYTHONPATH` 用 `src;windows`。

文档：

- [译文数据格式](docs/translation-format.md)
- [术语表](GLOSSARY.md)
- [架构决策](docs/adr)

## 发布

把 `VERSION` 改成新版本，合并到 main 后打标签：

```bash
git tag v<版本>
git push origin v<版本>
```

打标签就是对外发布。GitHub Actions 会先确认标签与 `VERSION` 一致，再构建三个发布包（macOS arm64、macOS x86_64、Windows x64）和 macOS 的 `install.sh`，全部成功后公开为正式 Release。`install.sh` 写死了版本号和 sha256，所以它只能配合同一次构建的发布包使用。

每个包内置对应系统的 Python 运行环境，按 `packaging/runtime.lock.json` 组装。升级依赖时运行 `scripts/lock_runtime.py` 更新这个锁定文件。想只构建不发布，可以手动运行 `release` 工作流；本地运行 `scripts/release.py` 只打当前系统的发布包。

创意工坊引流物品的文案与上传指引见 [workshop/](workshop/README.md)。

## 许可

- 安装器与脚本：MIT，见 [LICENSE](LICENSE)
- 译文：CC BY-NC-SA 4.0，见 [translations/LICENSE](translations/LICENSE)
