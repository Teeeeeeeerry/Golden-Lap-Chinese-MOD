import UnityPy
import pytest

from glzh.fonts import CJK_FONT_ASSET, add_cjk_fallback, missing_glyphs, required_chars


def test_required_chars_keeps_only_non_ascii_glyphs():
    assert required_chars(["生涯 Career", "{otherDriver} 超车！\n"]) == set("生涯超车！")


@pytest.fixture(scope="module")
def ui(game) -> bytes:
    return game.ui.read_bytes()


def font_assets(data: bytes) -> dict[int, dict]:
    out = {}
    for obj in UnityPy.load(data).objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if "m_FaceInfo" in tree:
            out[obj.path_id] = tree
    return out


def test_missing_glyphs_reports_only_chars_the_cjk_font_lacks(ui):
    assert missing_glyphs(ui, set("简体中文生涯赛车设置退出")) == set()
    assert missing_glyphs(ui, {""}) == {""}  # 私用区字符


def test_add_cjk_fallback_points_every_font_to_cjk_once(ui):
    before = font_assets(ui)
    after = font_assets(add_cjk_fallback(ui))
    cjk_id = next(i for i, t in after.items() if t["m_Name"] == CJK_FONT_ASSET)
    assert before.keys() == after.keys() and len(after) > 10
    for path_id, tree in after.items():
        chain = [(ref["m_FileID"], ref["m_PathID"]) for ref in tree.pop("m_FallbackFontAssetTable")]
        original = before[path_id].pop("m_FallbackFontAssetTable")
        if path_id != cjk_id:
            assert chain.count((0, cjk_id)) == 1
            # 原有后备顺序不变，中文字体只追加在末尾
            assert chain[: len(original)] == [(r["m_FileID"], r["m_PathID"]) for r in original]
        assert tree == before[path_id]
