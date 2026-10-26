# T1 字体注入最小验证：手法与结论

对应 issue #2。脚本：`spike/t1_font_spike.py`，测试：`spike/test_t1_font_spike.py`。

## 关键发现

1. **游戏已自带思源黑体。** `ui_assets_all` 包内有完整字体 `NotoSansSC-Black`（约 10 MB，含字体数据）和对应的动态 TMP 字体 `NotoSansSC-Black SDF`（`m_AtlasPopulationMode = 1`，运行时按需生成字形）。所以无需烘焙 SDF 图集，也无需随发布包分发字体文件。
2. **大多数界面文本已能显示中文。** 界面文本组件使用的字体：`Figtree-Bold SDF` 965 处、`Figtree-Black SDF` 238 处、`LiberationSans SDF` 87 处、`Figtree SDF` 21 处、`Figtree-BoldItalic SDF` 18 处。前两者的后备链已含 `NotoSansSC-Black SDF`，其余三者没有。
3. **catalog 校验每个包的 CRC。** `catalog.json` 的 `m_ExtraDataString`（base64 后的二进制，内嵌 UTF-16LE JSON）为每个包写了非零 `m_Crc`。改过的包 CRC 必然对不上，Unity 会拒绝加载。所以“`catalog.json` 无需改动”这一点不成立：CRC 值必须改，结构不用动。
4. **UnityPy 保存默认不压缩。** `env.file.save()` 会把 49 MB 的 `ui_assets_all` 写成约 2 GB，必须指定 `packer="lz4"`（写回后约 49 MB）。

## 注入步骤

1. 备份 `catalog.json`、土耳其语字符串表包、`ui_assets_all_*.bundle`；每次都从备份重打，因此可重复运行。若当前文件不是上次写入的补丁产物（按 sha256 判断，说明游戏已更新或被还原），先用当前文件刷新备份。
2. `ui_assets_all`：对包内每个 TMP 字体（`m_FaceInfo` 存在的 MonoBehaviour），若后备链 `m_FallbackFontAssetTable` 不含 `NotoSansSC-Black SDF`，就在末尾追加 `{m_FileID: 0, m_PathID: <它的 path_id>}`。只改引用，不新增对象，文件名不变。
3. 土耳其语字符串表包：按 `m_Id` 改 `m_Localized`（spike 只改了主菜单与设置页的 16 条 Menus）。
4. `catalog.json`：在解码后的 blob 中按字节匹配 UTF-16LE 的 `"m_Crc":<数字>`，替换为 `0` 加空格补齐原长度。JSON 允许空白，blob 内的长度前缀保持有效；只替换 base64 字符串本身，其余文本原样保留。

## 结论

- 自动校验（UnityPy 读回）通过：字符串表只有指定条目变化；所有 UI 字体的后备链都指向 `NotoSansSC-Black SDF`；catalog 中 15 个包的 CRC 均为 0、blob 长度不变。
- 注入后游戏可正常启动，`Player.log` 无 CRC / 资源包加载错误。
- 游戏内中文渲染：待人工确认，结果记在 issue #2。

## 对后续票的影响

- T3（#4）：写回土耳其语字符串表包后必须同步把 catalog 中的 CRC 置 0，并用 `packer="lz4"` 保存。
- T4（#5）：无需生成字体子集或烘焙 SDF，复用游戏自带 `NotoSansSC-Black SDF` 即可；代价是全部中文都是 Black 字重。若要更细字重，仍需按 ADR 0002 注入另一套思源黑体。ADR 0002 需据此复核；spike 把 catalog 中全部包的 CRC 都置 0，生产版应只清被改的包，并同步修订 ADR 0001 中“catalog 不改动”的表述。
