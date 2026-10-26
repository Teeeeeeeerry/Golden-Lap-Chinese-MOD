# Golden Lap 简体中文汉化

把 Golden Lap 的界面文本翻译成简体中文。汉化会顶替游戏中的「土耳其语」语言选项，装好后在设置里选择「简体中文」即可。

项目主页：https://github.com/Teeeeeeeerry/Golden-Lap-Chinese-MOD

## 安装

1. 准备 Python 3.11 或更新版本。macOS 自带的通常是 3.9，不够用；请从 https://www.python.org/downloads/macos/ 下载安装。
2. 解压本压缩包，双击 `install.command`。
   - 第一次打开会被 macOS 拦截（提示“无法验证开发者”）。请在访达中右键点 `install.command` → 打开 → 再点“打开”。
   - 也可以在终端运行 `xattr -dr com.apple.quarantine <解压后的文件夹>`，之后就能直接双击。
3. 首次运行会联网安装依赖，约 1 分钟。之后安装器会自动找到 Steam 中的 Golden Lap，备份原始文件并注入汉化，约需半分钟。
4. 启动游戏，进入设置 → 语言，选择「简体中文」。

安装器只在你的电脑上修改游戏文件，原始文件备份在 `~/Library/Application Support/GoldenLapZH/backup`。

## 游戏更新后

游戏更新，或在 Steam 中“验证游戏文件的完整性”后，汉化会被覆盖、界面恢复为土耳其语。再双击一次 `install.command` 即可。安装器会先备份新版本的原始文件，再重新注入。

## 卸载

双击 `restore.command`，游戏即恢复为未汉化状态，语言选项中的土耳其语也会恢复。确认不再需要后，可删除 `~/Library/Application Support/GoldenLapZH`。

如果备份丢失，还原脚本不会改动游戏。此时可在 Steam 中右键 Golden Lap → 属性 → 已安装文件 → 验证游戏文件的完整性，恢复原版。

## 常见问题

- **找不到游戏**：如果游戏装在 Steam 默认库以外、且没有被自动找到，可在终端设置环境变量后运行：`GOLDEN_LAP_APP="/你的路径/goldenlap.app" ./install.command`。
- **比赛界面还有英文**：比赛中的部分界面文本来自游戏的另一张表（Race UI），而土耳其语没有这张表，所以这部分文本保持英文。
- **译文质量**：当前译文是机翻初稿，欢迎到项目主页提交校对意见。
- **为什么占用土耳其语**：游戏无法新增语言选项，只能替换现有的一个。选择土耳其语后，就无法再使用土耳其语界面。

## 内容与许可

本压缩包只包含安装/还原脚本、Python 源码和译文，不含任何游戏原始资源，也不含字体。中文字形使用的是游戏自带的思源黑体。

- 脚本与源码：MIT 许可（见 `LICENSE`）
- 译文：CC BY-NC-SA 4.0（见 `translations/LICENSE`）
