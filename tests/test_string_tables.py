import UnityPy

from glzh.string_tables import localized_table, patch_string_tables, read_tables, rename_language_option
from glzh.translations import en_hash

CAREER = 248174071668736  # Menus：Career


def mono_behaviours(data: bytes) -> dict[int, dict]:
    env = UnityPy.load(data)
    return {o.path_id: o.read_typetree() for o in env.objects if o.type.name == "MonoBehaviour"}


def test_read_tables_by_collection_name(game):
    tables = read_tables(game.english.read_bytes())
    assert {"Content", "Menus", "Events"} <= tables.keys()
    assert tables["Menus"][CAREER] == "Career"


def test_localized_table_prefers_translation_and_falls_back_to_english():
    english = {1: "Career", 2: "Settings"}
    zh = {"1": {"en_hash": en_hash("Career"), "zh": "生涯", "status": "mt"}}
    assert localized_table(english, zh) == {1: "生涯", 2: "Settings"}


def test_localized_table_clears_rows_english_does_not_have():
    assert localized_table({1: "Career"}, {}, turkish_ids=[1, 7]) == {1: "Career", 7: ""}


def test_patch_string_tables_sets_given_ids_and_keeps_the_rest(game):
    original_bytes = game.turkish.read_bytes()
    original = read_tables(original_bytes)
    new_id = 999  # 土耳其语表中不存在的 m_Id 应被追加
    patched_bytes = patch_string_tables(original_bytes, {"Menus": {CAREER: "生涯", new_id: "新增"}})
    patched = read_tables(patched_bytes)
    assert patched["Menus"][CAREER] == "生涯" and patched["Menus"][new_id] == "新增"
    assert {k: v for k, v in patched["Menus"].items() if k not in (CAREER, new_id)} == {
        k: v for k, v in original["Menus"].items() if k != CAREER
    }
    assert patched["Content"] == original["Content"] and patched["Events"] == original["Events"]

    # 除表数据外，所有 MonoBehaviour 的其余字段（共享数据、元数据、语言 id 等）不变；原有行的元数据不变
    before, after = mono_behaviours(original_bytes), mono_behaviours(patched_bytes)
    assert before.keys() == after.keys()
    for path_id, tree in before.items():
        rows = tree.pop("m_TableData", [])
        new_rows = {row["m_Id"]: row for row in after[path_id].pop("m_TableData", [])}
        assert tree == after[path_id]
        assert all(new_rows[row["m_Id"]]["m_Metadata"] == row["m_Metadata"] for row in rows)
    # 必须压缩写回：未压缩时体积会膨胀数十倍
    assert len(patched_bytes) < 2 * len(original_bytes)


def test_rename_language_option_changes_only_turkish(game):
    before = mono_behaviours(game.locales.read_bytes())
    after = mono_behaviours(rename_language_option(game.locales.read_bytes(), "tr", "简体中文", "zh-CN"))
    turkish = next(path_id for path_id, t in before.items() if t.get("m_Identifier", {}).get("m_Code") == "tr")
    assert after[turkish]["m_LocaleName"] == "简体中文"
    assert after[turkish]["m_CustomFormatCultureCode"] == "zh-CN" and after[turkish]["m_UseCustomFormatter"] == 1
    assert {k: v for k, v in after.items() if k != turkish} == {k: v for k, v in before.items() if k != turkish}
