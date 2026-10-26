"""字体：让界面字体能显示中文。

ui_assets_all 包自带思源黑体（NotoSansSC-Black，约 3 万字形）及其动态 TMP 字体 `NotoSansSC-Black SDF`，
运行时按需生成字形。注入只需把它追加到包内其余 TMP 字体的后备链末尾，不新增对象、不分发字体（见 ADR 0003）。
"""

import io

import UnityPy
from fontTools.ttLib import TTFont

from glzh.bundles import PACKER, mono_behaviours

CJK_FONT_ASSET = "NotoSansSC-Black SDF"
DYNAMIC = 1  # m_AtlasPopulationMode：运行时按需生成字形


def required_chars(texts) -> set[str]:
    """译文实际用到的非 ASCII 字符（需要中文字体提供字形的部分）。"""
    return {ch for text in texts for ch in text if ord(ch) > 0x7F and not ch.isspace()}


def font_assets(env) -> list:
    """包内的 TMP 字体：[(对象, typetree)]。"""
    return [(obj, tree) for obj, tree in mono_behaviours(env) if "m_FaceInfo" in tree]


def _cjk_font(fonts: list):
    matches = [(obj, tree) for obj, tree in fonts if tree["m_Name"] == CJK_FONT_ASSET]
    if len(matches) != 1:
        raise ValueError(f"ui 包中应恰好有一个 {CJK_FONT_ASSET}，实际 {len(matches)} 个；游戏可能已不再自带思源黑体")
    obj, tree = matches[0]
    if tree["m_AtlasPopulationMode"] != DYNAMIC:
        # 静态图集只含预烘的字，按源字体检查覆盖就不成立了
        raise ValueError(f"{CJK_FONT_ASSET} 不再是动态字体，无法按需生成中文字形")
    return obj, tree


def missing_glyphs(bundle: bytes, chars: set[str]) -> set[str]:
    """chars 中中文字体源文件未覆盖的字符。"""
    env = UnityPy.load(bundle)
    _, cjk = _cjk_font(font_assets(env))
    source_id = cjk["m_SourceFontFile"]["m_PathID"]
    font = next(obj for obj in env.objects if obj.path_id == source_id).read_typetree()
    cmap = TTFont(io.BytesIO(bytes(font["m_FontData"]))).getBestCmap()
    return {ch for ch in chars if ord(ch) not in cmap}


def add_cjk_fallback(bundle: bytes) -> bytes:
    """把中文字体追加到包内其余 TMP 字体的后备链末尾（已含则跳过）。"""
    env = UnityPy.load(bundle)
    fonts = font_assets(env)
    cjk_id = _cjk_font(fonts)[0].path_id
    for obj, tree in fonts:
        chain = tree["m_FallbackFontAssetTable"]
        if obj.path_id == cjk_id or any(ref["m_FileID"] == 0 and ref["m_PathID"] == cjk_id for ref in chain):
            continue
        chain.append({"m_FileID": 0, "m_PathID": cjk_id})
        obj.save_typetree(tree)
    return env.file.save(packer=PACKER)
