import UnityPy
import pytest

from glzh.fonts import CJK_FONT_ASSET, add_cjk_fallback, font_assets, load_serialized, missing_glyphs, required_chars

PRIVATE_USE = "\ue000"  # 任何字体都不会有字形的私用区字符


def test_required_chars_keeps_only_non_ascii_glyphs():
    assert required_chars(["生涯 Career", "{otherDriver} 超车！\n"]) == set("生涯超车！")


@pytest.fixture(scope="module")
def ui(game) -> bytes:
    return game.ui.read_bytes()


def fonts_by_id(data: bytes) -> dict[int, dict]:
    return {obj.path_id: tree for obj, tree in font_assets(UnityPy.load(data))}


def test_missing_glyphs_reports_only_chars_the_cjk_font_lacks(ui):
    assert missing_glyphs(ui, set("简体中文生涯赛车设置退出")) == set()
    assert missing_glyphs(ui, {PRIVATE_USE}) == {PRIVATE_USE}


def test_add_cjk_fallback_points_every_font_to_cjk_once(ui):
    before = fonts_by_id(ui)
    after = fonts_by_id(add_cjk_fallback(ui))
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


def serialized_fonts(data: bytes, game) -> dict[int, dict]:
    """读回 resources.assets 这类无内嵌类型信息的序列化文件中的 TMP 字体。"""
    return {obj.path_id: tree for obj, tree in font_assets(load_serialized(data, game))}


def serialized_raw(data: bytes, game) -> dict[int, bytes]:
    return {obj.path_id: obj.get_raw_data() for obj in load_serialized(data, game).objects.values()}


def rename_serialized_font(game, old: str, new: str) -> None:
    serialized = load_serialized(game.resources.read_bytes(), game)
    obj, tree = next((o, t) for o, t in font_assets(serialized) if t["m_Name"] == old)
    tree["m_Name"] = new
    obj.save_typetree(tree)
    game.resources.write_bytes(serialized.save())
