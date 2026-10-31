# Golden Lap 汉化

为 Golden Lap 增加简体中文界面的社区汉化项目。

## Language

### 游戏侧

**界面文本**:
经本地化系统按语言提供的文本，即菜单、按钮、提示等 UI 文字。首期范围仅限于此。
_Avoid_: UI 字符串、localization 文本

**数据文本**:
车队、车手、赞助商、事件等游戏数据所含文字。不在首期范围内。
_Avoid_: 内容文本、剧情文本

**语言选项**:
游戏设置中可选的一种界面语言。土耳其语一项的内容整体替换为简体中文（含显示名），语言总数不变。
_Avoid_: Locale、语言包

**写死文本**:
直接写在 ui 包文本组件上、没有引用字符串表的界面文本（如主菜单的「our new game」）。汉化时为它在 Menus 表新增翻译条目并改为引用（见 ADR 0004）。
_Avoid_: 硬编码字符串

**字符串表**:
一种语言的一组翻译条目，按用途分为 Content、Menus、Events、Race UI 四张表，打包进该语言的本地化资源包。土耳其语原本没有 Race UI 表，汉化时新建并在 catalog 中登记（见 ADR 0005）。
_Avoid_: StringTable、文本表

**后备字体**:
TMP 字体缺字时按顺序回退取字形的字体。中文显示依赖把游戏自带的 `NotoSansSC-Black SDF` 追加到各界面字体的后备链，`ui_assets_all` 包与 `resources.assets` 两处各有一套界面字体，都要处理（见 ADR 0003）；注入时还把它的行度量按 Figtree 的比例对齐，免得含中文的行基线下移（见 ADR 0006）。
_Avoid_: fallback、备用字体

**官方 MOD**:
游戏自带 MOD 系统加载的数据包（JSON 与图片），同一时间仅能启用一个，可经 Steam 创意工坊订阅。
_Avoid_: 数据 MOD、工坊 MOD

### 项目侧

**安装器**:
在玩家本地读取游戏文件、就地注入译文并为界面字体挂上中文后备字体、并可还原的程序。本项目不做运行时注入，故无常驻插件。玩家通过一行安装命令（下载 Release 中的 `install.sh`，按芯片取发布包并校验 sha256）或双击发布包中的 `install.command` 运行它。
_Avoid_: 插件、hook、补丁器、mod 本体

**状态标签**:
排行榜每行右侧的深色标签，显示赛车状态：进站圈、出站圈、进站、退赛。它关闭了 maskable 才露在排行榜的遮罩面板外（文本组件 `StatusLabelText`）。
_Avoid_: 黑块、status pill

**子网格**:
TMP 为同一段文字里不同字体或不同图集的字形单独创建的网格（`TMP_SubMeshUI`）。后备字体和多图集第 2 张起的字形都画在这里。子网格不继承文本组件的 maskable。
_Avoid_: sub mesh、子对象

**专用字体**:
只给状态标签用的动态字体 `GoldenLapZH-StatusLabel SDF`，由注入器从 `NotoSansSC-Black SDF` 克隆，只有一张图集，中文画在主网格里（见 ADR 0008）。
_Avoid_: 标签字体

**构建**:
由译文文件与玩家本地的原始游戏文件生成待写回的字符串表包、locales 包、ui 包、`resources.assets`、`level2` 与 catalog 的过程，在玩家本地运行。
_Avoid_: 打包、编译

**翻译条目**:
一条可翻译的界面文本，由键、英文原文、译文、校对状态组成。
_Avoid_: 字符串、词条、entry

**校对状态**:
翻译条目译文的可信程度：机翻、已校对，或因英文原文变化而待复核。
_Avoid_: 审核状态、质量等级

**发布包**:
发到 GitHub Release 的 zip，含安装器、还原脚本、源码、译文、说明，以及内置的 Python 运行环境（ADR 0007），按芯片架构分包；不含游戏原始资源与字体。由 `scripts/release.py` 生成，同时生成一行安装命令用的 `install.sh`（写有版本号和各包的 sha256），三者一起上传到 GitHub Release。
_Avoid_: 安装包、补丁包

**更新比对**:
游戏更新后按 `m_Id` 比对当前英文原文哈希与译文的 `en_hash`，把翻译条目分为待译（新出现）、原文改动（置为待复核）、废弃（游戏里已没有）三类。
_Avoid_: diff、差分
