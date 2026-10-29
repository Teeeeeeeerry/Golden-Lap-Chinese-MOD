# Golden Lap 简体中文汉化

为 Golden Lap 增加简体中文界面：以简体中文顶替游戏的土耳其语语言选项，并让界面字体能显示中文。所有改动都在玩家本地完成，本仓库不含任何游戏原始资源。

## 安装（macOS）

需要 macOS 11 或更新版本，不用另外安装 Python。在「终端」里粘贴运行这一行：

```bash
/bin/bash -c "$(curl -fsSL https://github.com/Teeeeeeeerry/Golden-Lap-Chinese-MOD/releases/latest/download/install.sh)"
```

它会按芯片（Apple 芯片或 Intel）下载最新的发布包，校验 sha256 后解压到 `~/Library/Application Support/GoldenLapZH/app/<版本>`，再运行其中的安装器。用 curl 下载的文件不带隔离属性，所以不会被 macOS 拦截。卸载时在末尾加上 ` glzh restore`。

也可以到 Releases 页面下载对应芯片的发布包（`…-macos-arm64.zip` 或 `…-macos-x86_64.zip`），解压后双击 `install.command`；第一次打开会被 macOS 拦截（“无法验证开发者”），请在访达中右键点它 → 打开 → 再点“打开”。发布包自带 Python 运行环境，安装时不联网。安装器会自动查找 Steam 中的 Golden Lap，备份原始文件后注入汉化。装好后进入游戏，在设置的语言选项中选择“简体中文”（原土耳其语位置）。玩家说明见 [docs/release-README.md](docs/release-README.md)。

游戏更新或在 Steam 中“验证游戏文件完整性”后，汉化会被覆盖，再运行一次安装即可。原始文件备份在 `~/Library/Application Support/GoldenLapZH/backup`。若游戏不在 Steam 的默认位置且未被找到，可设置环境变量 `GOLDEN_LAP_APP` 指向 `goldenlap.app`。

## 卸载（还原）

在终端运行 `/bin/bash -c "$(curl -fsSL https://github.com/Teeeeeeeerry/Golden-Lap-Chinese-MOD/releases/latest/download/install.sh)" glzh restore`，或双击 `macos/restore.command`（发布包中为 `restore.command`），即可从备份恢复被改动的文件，游戏回到未汉化状态，语言选项中的土耳其语也会恢复。只还原仍是汉化版本的文件；已被游戏更新覆盖的文件本身就是原版，会跳过。若备份缺失，脚本不会改动游戏，并提示在 Steam 中“验证游戏文件完整性”恢复原版。确认不再需要后，可删除 `~/Library/Application Support/GoldenLapZH`。

## 发布

```bash
.venv/bin/python scripts/release.py
```

先校验译文，再在 `dist/` 生成两个发布包：`GoldenLap-zh-Hans-v<版本>-macos-arm64.zip`（Apple 芯片）和 `…-macos-x86_64.zip`（Intel）。项目文件只收录 git 跟踪的：安装器、还原脚本、源码、译文与玩家说明（`docs/release-README.md`），不含任何游戏原始资源或字体（ADR 0002、0003）。包里还内置独立的 Python 运行环境，玩家不用自己装 Python（ADR 0007）；它按 `packaging/runtime.lock.json` 组装，第一次构建要联网下载，之后用 `~/Library/Caches/GoldenLapZH-build` 里的缓存。升级依赖时运行 `scripts/lock_runtime.py` 重新生成锁定文件。同时生成一行命令用的 `install.sh`，其中写死了版本号和两个包的 sha256。把两个包和 `install.sh` 一起上传到 GitHub Release 即可（Release 的标签为 `v<版本>`，`install.sh` 按标签下载对应版本的包）。创意工坊引流物品的文案与上传指引见 [workshop/](workshop/README.md)。

## 开发

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

- 译文数据格式：[docs/translation-format.md](docs/translation-format.md)
- 校验译文：`PYTHONPATH=src .venv/bin/python -m glzh validate`
- 游戏更新后比对差异：`PYTHONPATH=src .venv/bin/python -m glzh diff [--write]`
- 构建到仓库外的目录（不改动游戏）：`PYTHONPATH=src .venv/bin/python -m glzh build <目录>`
- 术语见 [GLOSSARY.md](GLOSSARY.md)，架构决策见 [docs/adr](docs/adr)

## 许可

安装器与脚本：MIT（见 [LICENSE](LICENSE)）。译文：CC BY-NC-SA 4.0（见 [translations/LICENSE](translations/LICENSE)）。
