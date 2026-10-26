# 直接改游戏文件、以简体中文顶替土耳其语

**Status:** accepted

游戏采用 Unity Localization + Addressables，语言列表来自 `StreamingAssets/aa/` 中的本地化资源包。自带的创意工坊 MOD 系统仅加载 `Data/**/*.json` 与 `*.png`，无法触及界面文本、字体或代码，故创意工坊订阅不能实现汉化。

决定直接修改游戏文件：将 `localization-string-tables-turkish_assets_all.bundle` 内容整体替换为简体中文，并在 locales 包中把该语言显示名改为"简体中文"。

采用"顶替"而非"新增第 9 种语言"的原因：`catalog.json` 将键与条目存为 base64 二进制 blob，新增语言需手工重建这些 blob 并注册新包，极脆且难随版本维护；顶替现有语言包使用固定文件名，`catalog.json` 结构无需改动。选土耳其语因其在目标玩家群体中使用面相对最小。

**Considered Options:**
- **BepInEx 运行时注入**（否决）：可真正新增 locale、不碰游戏文件、游戏更新后基本照用，设置字体后备链仅需少量代码。否决理由为避免依赖第三方加载器；代价是本方案每次游戏更新后被覆盖，需重装。
- **二进制改 catalog 新增第 9 种语言**（否决）：维护成本与崩溃风险过高。

**Consequences:**
- 游戏每次更新覆盖被改文件，需重跑安装器；Steam"验证文件完整性"同样清除汉化。
- 土耳其语玩家无法再使用土耳其语。
- 中文正常显示须向 TMP 主字体 `LiberationSans SDF` 注入中文后备字形，而该字体资源位于体积较大、带内容哈希命名的 `ui_assets_all` 包中，为本方案工程风险最高处。
