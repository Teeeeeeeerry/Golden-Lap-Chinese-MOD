# Golden Lap 简体中文汉化（Windows）

把 Golden Lap 的界面文本翻译成简体中文。汉化会顶替游戏中的「土耳其语」语言选项，装好后在语言选项里选择「简体中文」。

项目主页：https://github.com/Teeeeeeeerry/Golden-Lap-Chinese-MOD

## 系统要求

Windows 10 或更新版本，64 位（x64）。不用另外安装 Python，运行环境已经包含在汉化里，安装时也不用联网。

## 安装

1. 先退出游戏。
2. 把压缩包完整解压到一个文件夹，不要在压缩软件里直接运行。
3. 双击 `install.bat`，等窗口显示「完成」。安装时要重新生成较大的资源文件，通常需要一两分钟。
4. 进入游戏，在设置的语言选项里选择「简体中文」。

如果 Windows 弹出「Windows 已保护你的电脑」，点「更多信息」，再点「仍要运行」。

## 找不到游戏时

安装器会从 Steam 的所有游戏库里查找 Golden Lap。如果仍然找不到，请打开命令提示符，先设置游戏目录（`goldenlap.exe` 所在的文件夹），再运行安装：

```
cd /d 解压出来的文件夹
set GOLDEN_LAP_DIR=D:\你的游戏目录\Golden Lap
install.bat
```

## 游戏更新后

游戏更新或在 Steam 中「验证游戏文件的完整性」后，汉化会被覆盖。再运行一次 `install.bat` 即可。

## 提示文件被占用时

退出游戏和正在扫描游戏文件的程序（比如杀毒软件）后重新运行，安装器会接着完成。

## 卸载

先退出游戏，再双击 `restore.bat`。游戏会恢复原版，语言选项里的土耳其语也会恢复。

原始文件备份在 `%LOCALAPPDATA%\GoldenLapZH\backup`。确认不再需要后，可以删除 `%LOCALAPPDATA%\GoldenLapZH` 文件夹。

如果备份丢失，还原脚本不会改动游戏。请在 Steam 中右键 Golden Lap → 属性 → 已安装文件 → 验证游戏文件的完整性，恢复原版。

## 许可

安装器与脚本：MIT。译文：CC BY-NC-SA 4.0。内置运行环境的第三方组件见 `runtime/THIRD-PARTY.md`。
