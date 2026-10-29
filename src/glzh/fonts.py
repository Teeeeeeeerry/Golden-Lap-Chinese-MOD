"""字体：让界面字体能显示中文。

游戏自带思源黑体（NotoSansSC-Black，约 3 万字形）及其动态 TMP 字体 `NotoSansSC-Black SDF`，运行时按需生成字形。
注入只需把它追加到同一文件内其余 TMP 字体的后备链末尾，开启它的多图集，并把它的行度量按 Figtree 的比例对齐，
不新增对象、不分发字体（见 ADR 0003、0006）。

需要处理两处，各有一套独立的 TMP 字体：
- Addressables 的 `ui_assets_all` 包：自带类型信息；
- Resources 目录的 `resources.assets`：没有内嵌类型信息，需用游戏程序集现场生成 typetree，
  且其 MonoBehaviour 引用 `globalgamemanagers.assets` 中的脚本，读取时要一并加载。
"""

import io

import UnityPy
from fontTools.ttLib import TTFont
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

from glzh.bundles import PACKER, mono_behaviours
from glzh.game import GameFiles

CJK_FONT_ASSET = "NotoSansSC-Black SDF"
LINE_METRICS_FONT = "Figtree-Bold SDF"  # 挂中文后备的主字体之一；Figtree 各字重行度量相同
LINE_METRICS = ("m_AscentLine", "m_DescentLine", "m_LineHeight")
DYNAMIC = 1  # m_AtlasPopulationMode：运行时按需生成字形


def required_chars(texts) -> set[str]:
    """译文实际用到的非 ASCII 字符（需要中文字体提供字形的部分）。"""
    return {ch for text in texts for ch in text if ord(ch) > 0x7F and not ch.isspace()}


def font_assets(container) -> list:
    """资源包或序列化文件中的 TMP 字体：[(对象, typetree)]。TMP 的 Sprite Asset 也有 m_FaceInfo，但没有字体后备链，排除。"""
    return [
        (obj, tree)
        for obj, tree in mono_behaviours(container)
        if "m_FaceInfo" in tree and "m_FallbackFontAssetTable" in tree
    ]


def _cjk_font(fonts: list):
    matches = [(obj, tree) for obj, tree in fonts if tree["m_Name"] == CJK_FONT_ASSET]
    if len(matches) != 1:
        raise ValueError(f"应恰好有一个 {CJK_FONT_ASSET}，实际 {len(matches)} 个；游戏可能已不再自带思源黑体")
    obj, tree = matches[0]
    if tree["m_AtlasPopulationMode"] != DYNAMIC:
        # 静态图集只含预烘的字，按源字体检查覆盖就不成立了
        raise ValueError(f"{CJK_FONT_ASSET} 不再是动态字体，无法按需生成中文字形")
    return obj, tree


def _missing(cjk_obj, cjk: dict, chars: set[str]) -> set[str]:
    source_id = cjk["m_SourceFontFile"]["m_PathID"]  # 源字体与 TMP 字体在同一文件内（m_FileID 为 0）
    font = cjk_obj.assets_file.objects[source_id].read_typetree()
    cmap = TTFont(io.BytesIO(bytes(font["m_FontData"]))).getBestCmap()
    return {ch for ch in chars if ord(ch) not in cmap}


def ensure_glyphs(missing: set[str]) -> None:
    if missing:
        raise ValueError(f"中文字体缺少这些字的字形：{''.join(sorted(missing))}")


def _has_fallback(tree: dict, cjk_id: int) -> bool:
    return any(ref["m_FileID"] == 0 and ref["m_PathID"] == cjk_id for ref in tree["m_FallbackFontAssetTable"])


def _append_fallback(fonts: list, cjk_id: int) -> None:
    for obj, tree in fonts:
        if obj.path_id == cjk_id or _has_fallback(tree, cjk_id):
            continue
        chain = tree["m_FallbackFontAssetTable"]
        chain.append({"m_FileID": 0, "m_PathID": cjk_id})
        obj.save_typetree(tree)


def _enable_multi_atlas(cjk_obj, cjk: dict) -> None:
    """单张 1024² 动态图集只装得下约 90 个中文字，写满后新字显示为方框；开启后 TMP 写满即加开新图集（见 ADR 0003）。"""
    if not cjk["m_IsMultiAtlasTexturesEnabled"]:
        cjk["m_IsMultiAtlasTexturesEnabled"] = 1
        cjk_obj.save_typetree(cjk)


def _align_line_metrics(fonts: list, cjk_obj, cjk: dict) -> None:
    """把中文字体的上沿、下沿、行高改成与 Figtree 相同的比例（见 ADR 0006）。

    TMP 排一行时取各字形所属字体的最大上沿，思源黑体上沿 1.16em、Figtree 0.95em：
    一行里只要有中文，基线就下移，与旁边纯数字的文本框对不齐。按比例重算，重复执行结果不变。
    """
    refs = [tree for _, tree in fonts if tree["m_Name"] == LINE_METRICS_FONT]
    if len(refs) != 1:
        raise ValueError(f"应恰好有一个 {LINE_METRICS_FONT}，实际 {len(refs)} 个；无法对齐中文字体的行度量")
    ref, face = refs[0]["m_FaceInfo"], cjk["m_FaceInfo"]
    scale = face["m_PointSize"] / ref["m_PointSize"]
    for key in LINE_METRICS:
        face[key] = ref[key] * scale
    cjk_obj.save_typetree(cjk)


def missing_glyphs(bundle: bytes, chars: set[str]) -> set[str]:
    """chars 中 ui 包内中文字体源文件未覆盖的字符。"""
    return _missing(*_cjk_font(font_assets(UnityPy.load(bundle))), chars)


def inject_cjk_fallback(env) -> None:
    """在已加载的 ui 包中，把中文字体追加到其余 TMP 字体的后备链末尾（已含则跳过），开启它的多图集并对齐行度量。"""
    fonts = font_assets(env)
    cjk_obj, cjk = _cjk_font(fonts)
    _append_fallback(fonts, cjk_obj.path_id)
    _enable_multi_atlas(cjk_obj, cjk)
    _align_line_metrics(fonts, cjk_obj, cjk)


def add_cjk_fallback(bundle: bytes) -> bytes:
    """inject_cjk_fallback 的字节进出版本。"""
    env = UnityPy.load(bundle)
    inject_cjk_fallback(env)
    return env.file.save(packer=PACKER)


def load_serialized(data: bytes, deps: GameFiles):
    """加载 resources.assets 这类没有内嵌类型信息的序列化文件。

    deps 提供只读依赖：程序集（生成 typetree）与 globalgamemanagers.assets（脚本引用）。
    """
    env = UnityPy.Environment()
    env.load_file(deps.globalgamemanagers.read_bytes(), name=deps.globalgamemanagers.name, is_dependency=True)
    serialized = env.load_file(data, name=deps.resources.name)
    generator = TypeTreeGenerator(serialized.unity_version)
    generator.load_local_dll_folder(str(deps.managed))
    env.typetree_generator = generator
    return serialized


def add_cjk_fallback_serialized(data: bytes, deps: GameFiles, chars: set[str]) -> bytes:
    """resources.assets：检查中文字体覆盖 chars 后，把它追加到其余 TMP 字体的后备链末尾，开启它的多图集并对齐行度量。"""
    serialized = load_serialized(data, deps)
    fonts = font_assets(serialized)
    cjk_obj, cjk = _cjk_font(fonts)
    ensure_glyphs(_missing(cjk_obj, cjk, chars))
    _append_fallback(fonts, cjk_obj.path_id)
    _enable_multi_atlas(cjk_obj, cjk)
    _align_line_metrics(fonts, cjk_obj, cjk)
    return serialized.save()


def is_injected_serialized(data: bytes, deps: GameFiles) -> bool:
    """resources.assets 是否已被注入。

    判据：原版只有 Figtree-Black/Bold 等少数字体挂了中文后备，注入后其余字体全部都有。
    若将来原版本身就让所有字体都挂上中文后备，此判据会误报，需要改用别的标记。
    """
    fonts = font_assets(load_serialized(data, deps))
    cjk_id = _cjk_font(fonts)[0].path_id
    others = [tree for obj, tree in fonts if obj.path_id != cjk_id]
    return bool(others) and all(_has_fallback(tree, cjk_id) for tree in others)
