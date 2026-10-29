# 内置运行环境的第三方组件

发布包的 `runtime/python/` 是一份独立的 Python 运行环境，玩家不用自己安装 Python（见仓库 ADR 0007）。各组件都允许再分发，许可证随包附上：

| 组件 | 用途 | 许可 | 许可证位置 |
| --- | --- | --- | --- |
| CPython 3.12（python-build-standalone 构建） | Python 解释器与标准库 | CPython 为 PSF-2.0，内含组件各自的许可；python-build-standalone 构建项目本身为 MPL-2.0 | `lib/python3.12/LICENSE.txt`、`LICENSE.python-build-standalone.txt` |
| UnityPy | 读写 Unity 资源包 | MIT | `site-packages/unitypy-*.dist-info/` |
| fonttools | 检查中文字体的字形覆盖 | MIT | `site-packages/fonttools-*.dist-info/` |
| TypeTreeGeneratorAPI | 为 `resources.assets` 现场生成类型信息 | MIT | `site-packages/typetreegeneratorapi-*.dist-info/` |
| astc-encoder-py、etcpak、texture2ddecoder | UnityPy 的纹理编解码 | MIT | 各自的 `*.dist-info/` |
| Pillow | UnityPy 的图像处理 | MIT-CMU | `site-packages/pillow-*.dist-info/` |
| brotli、lz4 | 资源包压缩 | MIT、BSD-3-Clause | 各自的 `*.dist-info/` |
| attrs、fsspec | UnityPy 的依赖 | MIT、BSD-3-Clause | 各自的 `*.dist-info/` |
| tpk_ar | UnityPy 的类型数据读取 | MIT | `site-packages/tpk_ar-*.dist-info/LICENSE` |

不随包分发：`fmod_toolkit`。它内含商业授权的 FMOD 引擎，UnityPy 只在导出音频时才用到，汉化不处理音频。

版本、下载地址和 sha256 锁定在仓库的 `packaging/runtime.lock.json` 中。
