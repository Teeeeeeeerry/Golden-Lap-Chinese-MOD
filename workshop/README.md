# 创意工坊引流物品

在 Steam 创意工坊放一个**只有说明、不含汉化内容**的物品，用来把玩家引到 GitHub 下载安装器。游戏自带的 MOD 系统无法替换界面文本和字体（ADR 0001），而且发布内容本体会涉及再分发问题（ADR 0002），所以工坊只做引流。

## 物品内容

- **标题**：Golden Lap 简体中文汉化（说明页 / Chinese Localization Info）
- **描述**：`description.txt`（Steam BBCode 格式，直接粘贴）
- **预览图**：一张汉化后的游戏主菜单截图，命名为 `header_image.png` 或 `header_image.jpg`，自行截取，不放进仓库。
- **MOD 本体**：工坊物品需要以官方 MOD 的形式上传。放一个不含任何数据改动的最小 MOD，不要放译文或游戏资源。官方文档没有说明只放预览图能否提交，需要先私密提交一次确认；不行的话按文档下载 `BaseMod.zip` 做最小 MOD，使用前先看它附带的许可。注意：官方 MOD 同一时间只能启用一个，玩家若启用了这个说明物品，会顶掉原本启用的 MOD，所以简介里要写明“无需启用”。

## 上传步骤（人工）

步骤来自官方的 [Golden Lap Modding Documentation](https://funselektor.notion.site/Golden-Lap-Modding-Documentation-2bc95ac5902b492fa3ca204cddde0a4e)。

1. 在 Steam 库把筛选切到「工具」，安装并启动 `Golden Lap - Workshop Items Uploader`。
2. 输入标题，按 **Create Item**，工具会分配一个 ID。
3. 填写 Title，把 `description.txt` 粘贴到 Description，Visibility 先设为 Private 或 Friends Only。
4. 按 **Open folder**，把 MOD 内容和预览图放进打开的数据文件夹。
5. 回到工具按 **Submit**。
6. 到 Steam 物品页检查文字和链接，确认无误后把可见性改为 Public。

每次发布新版本后，不需要更新工坊物品：一行命令始终安装最新版，链接指向项目主页。如果安装方式变了，才需要更新 `description.txt` 并重新粘贴。
