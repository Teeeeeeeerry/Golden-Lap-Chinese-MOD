from glzh.build import build
from glzh.catalog import bundle_crcs
from glzh.game import LOCALES_BUNDLE, TURKISH_BUNDLE
from glzh.string_tables import read_tables
from glzh.translations import TABLES, en_hash, save_table

CAREER = 248174071668736


def test_build_writes_translations_english_fallback_and_zeroes_crc(game, tmp_path):
    for table in TABLES:
        save_table(tmp_path, table, {})
    save_table(tmp_path, "Menus", {str(CAREER): {"en_hash": en_hash("Career"), "zh": "生涯", "status": "mt"}})

    outputs = build(game, tmp_path)

    assert set(outputs) == {"catalog.json", f"StandaloneOSX/{TURKISH_BUNDLE}", f"StandaloneOSX/{LOCALES_BUNDLE}"}
    tables = read_tables(outputs[f"StandaloneOSX/{TURKISH_BUNDLE}"])
    english = read_tables(game.english.read_bytes())
    assert tables["Menus"][CAREER] == "生涯"
    # 未翻译的条目显示英文原文，而不是土耳其语
    assert all(tables[t][i] == english[t][i] for t in TABLES for i in english[t] if i != CAREER)
    crcs = bundle_crcs(outputs["catalog.json"].decode("utf-8"))
    assert crcs[TURKISH_BUNDLE] == 0 and crcs[LOCALES_BUNDLE] == 0
