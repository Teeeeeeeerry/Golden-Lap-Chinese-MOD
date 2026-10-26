import UnityPy

from glzh.string_tables import localized_table, patch_string_tables, read_tables, rename_locale
from glzh.translations import en_hash

CAREER = 248174071668736  # Menus：Career


def test_read_tables_by_collection_name(game):
    tables = read_tables(game.english.read_bytes())
    assert {"Content", "Menus", "Events"} <= tables.keys()
    assert tables["Menus"][CAREER] == "Career"


def test_localized_table_prefers_translation_and_falls_back_to_english():
    english = {1: "Career", 2: "Settings"}
    zh = {"1": {"en_hash": en_hash("Career"), "zh": "生涯", "status": "mt"}}
    assert localized_table(english, zh) == {1: "生涯", 2: "Settings"}


def test_patch_string_tables_sets_given_ids_and_keeps_the_rest(game):
    original = read_tables(game.turkish.read_bytes())
    new_id = 999  # 土耳其语表中不存在的 m_Id 应被追加
    patched = read_tables(patch_string_tables(game.turkish.read_bytes(), {"Menus": {CAREER: "生涯", new_id: "新增"}}))
    assert patched["Menus"][CAREER] == "生涯" and patched["Menus"][new_id] == "新增"
    assert {k: v for k, v in patched["Menus"].items() if k not in (CAREER, new_id)} == {
        k: v for k, v in original["Menus"].items() if k != CAREER
    }
    assert patched["Content"] == original["Content"] and patched["Events"] == original["Events"]


def test_rename_locale_changes_only_turkish_display_name(game):
    def names(data):
        env = UnityPy.load(data)
        return {
            t["m_Identifier"]["m_Code"] + "/" + t["m_Name"]: t["m_LocaleName"]
            for t in (o.read_typetree() for o in env.objects if o.type.name == "MonoBehaviour")
        }

    before = names(game.locales.read_bytes())
    after = names(rename_locale(game.locales.read_bytes(), "tr", "简体中文"))
    assert after["tr/Turkish (tr)"] == "简体中文"
    assert {k: v for k, v in after.items() if k != "tr/Turkish (tr)"} == {
        k: v for k, v in before.items() if k != "tr/Turkish (tr)"
    }
