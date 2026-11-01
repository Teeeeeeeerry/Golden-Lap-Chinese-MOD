# IL2CPP 版借用 ui 包内嵌的 typetree

**Status:** accepted

`resources.assets` 和 `level2` 没有内嵌类型信息。macOS 版用 `Managed` 目录的程序集现场生成 typetree，但 Windows 版是 IL2CPP 打包，没有这个目录。`ui_assets_all` 包内嵌了 `TMP_FontAsset` 和 `FunTextTMP` 的 typetree，而这两种类型正是注入要读写的。

决定：游戏是 IL2CPP 打包时，从 ui 包里取这两种类型的 typetree，用来读写 `resources.assets` 和 `level2`。Mono 打包的 macOS 版继续用 `Managed`。

探针在 Windows 版（Unity 2022.3.62f2）上读出了 `resources.assets` 的 18 个字体和 `level2` 的 298 个 `FunTextTMP`，全部成功，其中包括 `NotoSansSC-Black SDF`。

**Considered Options:**
- **用 `load_il2cpp` 从 `GameAssembly.dll` 现场生成**（否决）：生成器能加载，也能取到节点，但接入 UnityPy 后读出 0 个字体，继续排查的成本和结果都不确定。
- **导出 typetree 随仓库提交**（否决）：不依赖游戏结构，但每次游戏更新都可能要重新生成。
- **两个平台都改用借用方案**（否决）：路径更少，但 macOS 现有方案已验证可用，而本次没有 Mac 实机回归。

**Consequences:**
- 依赖 ui 包里一直存在这两种类型的对象。找不到时，安装器在写入任何文件之前报错退出。
- 写回两个文件还没有验证，要在第一个里程碑里进游戏确认。
