import pytest

from glzh.build import build
from glzh.catalog import bundle_crcs
from glzh.game import LOCALES_BUNDLE, TURKISH_BUNDLE
from glzh.string_tables import read_tables
from glzh.translations import TABLES, en_hash, save_table
from tests.test_fonts import PRIVATE_USE, fonts_by_id, edit_serialized_font, serialized_fonts, serialized_raw
from tests.test_string_tables import mono_behaviours

CAREER = 248174071668736
AA = "StreamingAssets/aa"


def write_translations(directory, zh):
    for table in TABLES:
        save_table(directory, table, {})
    save_table(directory, "Menus", {str(CAREER): {"en_hash": en_hash("Career"), "zh": zh, "status": "mt"}})


@pytest.fixture(scope="module")
def outputs(game, tmp_path_factory):
    directory = tmp_path_factory.mktemp("translations")
    write_translations(directory, "生涯")
    return build(game, directory)


def test_build_outputs_keep_original_file_names(game, outputs):
    assert set(outputs) == {
        f"{AA}/catalog.json",
        f"{AA}/StandaloneOSX/{TURKISH_BUNDLE}",
        f"{AA}/StandaloneOSX/{LOCALES_BUNDLE}",
        f"{AA}/StandaloneOSX/{game.ui.name}",
        "resources.assets",
    }


def test_build_writes_translations_with_english_fallback(game, outputs):
    tables = read_tables(outputs[f"{AA}/StandaloneOSX/{TURKISH_BUNDLE}"])
    english = read_tables(game.english.read_bytes())
    assert tables["Menus"][CAREER] == "生涯"
    # 未翻译的条目显示英文原文，而不是土耳其语
    assert all(tables[t][i] == english[t][i] for t in TABLES for i in english[t] if i != CAREER)
    names = [t.get("m_LocaleName") for t in mono_behaviours(outputs[f"{AA}/StandaloneOSX/{LOCALES_BUNDLE}"]).values()]
    assert "简体中文" in names and "Turkish" not in names


def test_build_injects_cjk_fallback_and_zeroes_crc_of_patched_bundles(game, outputs):
    fonts = fonts_by_id(outputs[f"{AA}/StandaloneOSX/{game.ui.name}"])
    cjk_id = next(i for i, t in fonts.items() if t["m_Name"] == "NotoSansSC-Black SDF")
    assert all(
        any((ref["m_FileID"], ref["m_PathID"]) == (0, cjk_id) for ref in t["m_FallbackFontAssetTable"]) for i, t in fonts.items() if i != cjk_id
    )
    crcs = bundle_crcs(outputs[f"{AA}/catalog.json"].decode("utf-8"))
    patched = {TURKISH_BUNDLE, LOCALES_BUNDLE, game.ui.name}
    assert all(crcs[name] == 0 for name in patched)
    assert all(crc != 0 for name, crc in crcs.items() if name not in patched)


def test_build_refuses_translations_the_cjk_font_cannot_render(game, tmp_path):
    write_translations(tmp_path, "生涯" + PRIVATE_USE)
    with pytest.raises(ValueError, match="缺少"):
        build(game, tmp_path)


def test_build_injects_cjk_fallback_into_resources_assets(game, outputs):
    """resources.assets 是 Resources 目录的序列化文件，自带一套 TMP 字体，不经 catalog 加载。"""
    before = serialized_fonts(game.resources.read_bytes(), game)
    after = serialized_fonts(outputs["resources.assets"], game)
    cjk_id = next(i for i, t in after.items() if t["m_Name"] == "NotoSansSC-Black SDF")
    assert before.keys() == after.keys() and len(after) > 10
    for path_id, tree in after.items():
        chain = [(r["m_FileID"], r["m_PathID"]) for r in tree.pop("m_FallbackFontAssetTable")]
        original = [(r["m_FileID"], r["m_PathID"]) for r in before[path_id].pop("m_FallbackFontAssetTable")]
        if path_id != cjk_id:
            assert chain.count((0, cjk_id)) == 1 and chain[: len(original)] == original
        assert tree == before[path_id]
    # 字体以外的对象逐字节不变
    raw_before, raw_after = serialized_raw(game.resources.read_bytes(), game), serialized_raw(outputs["resources.assets"], game)
    assert raw_before.keys() == raw_after.keys()
    assert all(raw_after[i] == raw for i, raw in raw_before.items() if i not in after)


def test_build_refuses_when_resources_assets_lacks_cjk_font(fake_game, tmp_path):
    edit_serialized_font(fake_game, "NotoSansSC-Black SDF", m_Name="Renamed SDF")
    write_translations(tmp_path, "生涯")
    with pytest.raises(ValueError, match="思源黑体"):
        build(fake_game, tmp_path)


def test_build_refuses_when_resources_assets_cjk_font_is_not_dynamic(fake_game, tmp_path):
    edit_serialized_font(fake_game, "NotoSansSC-Black SDF", m_AtlasPopulationMode=0)
    write_translations(tmp_path, "生涯")
    with pytest.raises(ValueError, match="动态字体"):
        build(fake_game, tmp_path)
