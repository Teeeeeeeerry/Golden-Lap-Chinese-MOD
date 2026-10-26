"""字体：让界面字体能显示中文。

ui_assets_all 包自带思源黑体（NotoSansSC-Black，约 3 万字形）及其动态 TMP 字体 `NotoSansSC-Black SDF`，
运行时按需生成字形。注入只需把它追加到包内其余 TMP 字体的后备链末尾，不新增对象、不分发字体（见 ADR 0003）。
"""

import io

import UnityPy
from fontTools.ttLib import TTFont

CJK_FONT_ASSET = "NotoSansSC-Black SDF"
PACKER = "lz4"


def required_chars(texts) -> set[str]:
    """译文实际用到的非 ASCII 字符（需要中文字体提供字形的部分）。"""
    return {ch for text in texts for ch in text if ord(ch) > 0x7F and not ch.isspace()}


def _font_assets(env):
    """包内的 TMP 字体：(对象, typetree)。"""
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:  # 部分 MonoBehaviour 缺类型信息，读不出来，跳过
            continue
        if "m_FaceInfo" in tree:
            yield obj, tree


def missing_glyphs(bundle: bytes, chars: set[str]) -> set[str]:
    """chars 中中文字体源文件未覆盖的字符。"""
    env = UnityPy.load(bundle)
    cjk = next(tree for _, tree in _font_assets(env) if tree["m_Name"] == CJK_FONT_ASSET)
    source_id = cjk["m_SourceFontFile"]["m_PathID"]
    font = next(obj for obj in env.objects if obj.path_id == source_id).read_typetree()
    cmap = TTFont(io.BytesIO(bytes(font["m_FontData"]))).getBestCmap()
    return {ch for ch in chars if ord(ch) not in cmap}


def add_cjk_fallback(bundle: bytes) -> bytes:
    """把中文字体追加到包内其余 TMP 字体的后备链末尾（已含则跳过）。"""
    env = UnityPy.load(bundle)
    fonts = list(_font_assets(env))
    cjk_ids = [obj.path_id for obj, tree in fonts if tree["m_Name"] == CJK_FONT_ASSET]
    if len(cjk_ids) != 1:
        raise ValueError(f"ui 包中应恰好有一个 {CJK_FONT_ASSET}，实际 {len(cjk_ids)} 个")
    cjk_id = cjk_ids[0]
    for obj, tree in fonts:
        chain = tree["m_FallbackFontAssetTable"]
        if obj.path_id == cjk_id or any(ref["m_FileID"] == 0 and ref["m_PathID"] == cjk_id for ref in chain):
            continue
        chain.append({"m_FileID": 0, "m_PathID": cjk_id})
        obj.save_typetree(tree)
    return env.file.save(packer=PACKER)
