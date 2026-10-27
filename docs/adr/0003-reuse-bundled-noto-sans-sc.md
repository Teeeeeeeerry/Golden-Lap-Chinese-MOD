# 复用游戏自带的思源黑体，不再烘焙和分发字体子集

**Status:** accepted（取代 ADR 0002 中"按译文用字做静态 SDF 子集并注入"的部分）

T1 最小验证（`docs/spike/t1-font-injection.md`）发现 `ui_assets_all` 包已自带完整的思源黑体 `NotoSansSC-Black`（约 3 万字形）及其动态 TMP 字体 `NotoSansSC-Black SDF`，运行时按需生成字形；占界面文本约九成的 `Figtree-Bold SDF`、`Figtree-Black SDF` 的后备链已含它。

决定：不烘焙 SDF 子集，也不随发布包分发字体。安装器只把 `NotoSansSC-Black SDF` 追加到 `ui_assets_all` 包内其余 TMP 字体后备链的末尾（只改引用，不新增对象，包文件名不变）。构建时由全部译文推导所需字形集合，检查思源黑体是否都有字形，缺字即中止构建。

理由：
- 无需新增 Texture2D/Material/TMP 字体对象，注入只改引用，风险远低于往包里塞新资源。
- 动态字体按需出字，补繁体也无需重烘，只要字体覆盖即可。
- 发布包只剩译文与脚本，彻底不含字体，许可与体积都更简单；思源黑体本身是 SIL OFL，ADR 0002 的字体许可约束仍然满足。

**Considered Options:**
- **按 ADR 0002 烘焙思源黑体 Regular/Medium 的静态 SDF 子集并注入**（否决）：需在包内新建多类对象并维护跨版本的对象引用，工程风险最高处更难；收益只是字重更细。
- **把自带 `NotoSansSC-Black` 的字体数据替换为更细字重的子集**（暂不采用）：TMP 字体的度量按 Black 计算，换字重可能导致行高偏差，留作日后优化。

**Consequences:**
- 中文全部为 Black 字重。界面主体用 Figtree Bold/Black，视觉上协调。
- 中文显示依赖游戏继续自带这款字体；若某次更新移除它，构建会因找不到 `NotoSansSC-Black SDF` 而中止，需改回自带字体方案。

**补充（#21）：** 游戏有两套独立的 TMP 字体。除 Addressables 的 `ui_assets_all` 包外，Resources 目录的 `resources.assets` 中也有一套，同样自带 `NotoSansSC-Black SDF`。经 Resources 加载的界面（如主菜单底部的反馈栏）用的是后一套，原版只有 `Figtree-Black SDF`、`Figtree-Bold SDF` 挂了中文后备。因此两处都按同样方式注入。`resources.assets` 没有内嵌类型信息，构建时用游戏 `Managed` 目录下的程序集现场生成 typetree（新增依赖 `TypeTreeGeneratorAPI`），并一并加载 `globalgamemanagers.assets` 以解析脚本引用；类型信息只在内存中使用，不落盘、不分发。`resources.assets` 不经 catalog 加载，无需改 CRC。
