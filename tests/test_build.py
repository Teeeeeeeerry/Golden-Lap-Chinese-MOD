import pytest

from glzh.build import build
from glzh.catalog import bundle_crcs
from glzh.game import ENGLISH_BUNDLE, LOCALES_BUNDLE, SHARED_BUNDLE, TURKISH_BUNDLE
from glzh.hardcoded import entry_id, save_hardcoded
from glzh.string_tables import read_tables
from glzh.translations import TABLES, en_hash, save_table
from tests.test_fonts import PRIVATE_USE, fonts_by_id, edit_serialized_font, serialized_fonts, serialized_raw
from tests.test_string_tables import mono_behaviours

CAREER = 248174071668736
AA = "StreamingAssets/aa"


OUR_NEW_GAME = "main_menu/our_new_game"


def write_translations(directory, zh):
    for table in TABLES:
        save_table(directory, table, {})
    save_table(directory, "Menus", {str(CAREER): {"en_hash": en_hash("Career"), "zh": zh, "status": "mt"}})
    save_hardcoded(directory, {OUR_NEW_GAME: {"en_hash": en_hash("our new game"), "zh": "我们的新游戏", "status": "mt"}})


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
        f"{AA}/StandaloneOSX/{SHARED_BUNDLE}",
        f"{AA}/StandaloneOSX/{ENGLISH_BUNDLE}",
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
    patched = {TURKISH_BUNDLE, LOCALES_BUNDLE, game.ui.name, SHARED_BUNDLE, ENGLISH_BUNDLE}
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
        else:
            assert tree.pop("m_IsMultiAtlasTexturesEnabled") == 1 and before[path_id].pop("m_IsMultiAtlasTexturesEnabled") == 0
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


def text_components(data: bytes) -> dict[int, dict]:
    """ui 包内带本地化引用字段的文本组件。"""
    return {i: t for i, t in mono_behaviours(data).items() if "textLocalization" in t}


def test_build_localizes_hardcoded_text_without_changing_other_languages(game, outputs):
    """写死的「our new game」改为引用新增的 Menus 条目：英文行写原文，土耳其语行写中文。"""
    m_id = entry_id(OUR_NEW_GAME)
    before = text_components(game.ui.read_bytes())
    after = text_components(outputs[f"{AA}/StandaloneOSX/{game.ui.name}"])
    target = [i for i, t in before.items() if t["m_text"] == "our new game"]
    assert len(target) == 1
    ref = after[target[0]]["textLocalization"]
    assert ref["m_TableReference"]["m_TableCollectionName"] == "GUID:b2f094414a933be4ca0323c14a8a1064"  # Menus
    assert ref["m_TableEntryReference"]["m_KeyId"] == m_id
    # 组件的其余字段与其他组件都不变
    assert {k: v for k, v in after[target[0]].items() if k != "textLocalization"} == {
        k: v for k, v in before[target[0]].items() if k != "textLocalization"
    }
    assert all(after[i] == t for i, t in before.items() if i != target[0])

    shared = [t for t in mono_behaviours(outputs[f"{AA}/StandaloneOSX/{SHARED_BUNDLE}"]).values() if t.get("m_TableCollectionName") == "Menus"][0]
    assert {"m_Id": m_id, "m_Key": f"glzh/{OUR_NEW_GAME}", "m_Metadata": {"m_Items": []}} in shared["m_Entries"]
    english = read_tables(outputs[f"{AA}/StandaloneOSX/{ENGLISH_BUNDLE}"])
    original_english = read_tables(game.english.read_bytes())
    assert english["Menus"][m_id] == "our new game"
    assert {t: {i: v for i, v in rows.items() if i != m_id} for t, rows in english.items()} == original_english
    assert read_tables(outputs[f"{AA}/StandaloneOSX/{TURKISH_BUNDLE}"])["Menus"][m_id] == "我们的新游戏"


def test_build_enables_multi_atlas_on_cjk_font(game, outputs):
    """单张 1024² 动态图集只装得下约 90 个中文字，写满后新字成方框；开启多图集后 TMP 会加开新图集。"""
    for fonts in (fonts_by_id(outputs[f"{AA}/StandaloneOSX/{game.ui.name}"]), serialized_fonts(outputs["resources.assets"], game)):
        cjk = next(t for t in fonts.values() if t["m_Name"] == "NotoSansSC-Black SDF")
        assert cjk["m_IsMultiAtlasTexturesEnabled"] == 1
