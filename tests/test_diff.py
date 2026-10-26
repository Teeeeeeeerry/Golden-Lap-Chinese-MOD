from glzh.diff import REPORT_ID_LIMIT, TableDiff, diff_against_english, diff_table, format_report
from glzh.string_tables import read_tables
from glzh.translations import TABLES, en_hash, save_table

A, B, C = "a" * 16, "b" * 16, "c" * 16


def item(en_hash, status="ok"):
    return {"en_hash": en_hash, "zh": "译文", "status": status}


def test_new_m_id_is_reported_as_untranslated():
    d = diff_table({"1": A, "2": B}, {"1": item(A)})
    assert (d.new, d.changed, d.obsolete) == (["2"], [], [])


def test_changed_source_is_reported_and_marked_stale():
    d = diff_table({"1": C}, {"1": item(A)})
    assert (d.new, d.changed, d.obsolete, d.stale) == ([], ["1"], [], ["1"])
    # 记下新哈希、置 stale：译文保留待复核，下次比对不再重复报出
    assert d.updated["1"] == {"en_hash": C, "zh": "译文", "status": "stale"}


def test_vanished_m_id_is_reported_as_obsolete_and_kept():
    d = diff_table({}, {"1": item(A)})
    assert (d.new, d.changed, d.obsolete) == ([], [], ["1"])
    assert d.updated == {"1": item(A)}


def test_source_turned_empty_is_a_change_not_obsolete():
    d = diff_table({"1": en_hash(""), "2": en_hash("")}, {"1": item(A)}, untranslatable={"1", "2"})
    assert (d.new, d.changed, d.obsolete) == ([], ["1"], [])


def test_already_stale_items_stay_counted_for_review():
    d = diff_table({"1": A}, {"1": item(A, status="stale")})
    assert (d.changed, d.stale) == ([], ["1"])


def test_lists_are_sorted_by_numeric_m_id():
    assert diff_table({"10": A, "9": A}, {}).new == ["9", "10"]


def test_format_report_summarises_each_table_and_truncates_long_lists():
    many = [str(i) for i in range(REPORT_ID_LIMIT + 2)]
    text = format_report({"Menus": TableDiff(new=many, changed=["1"], stale=["1", "5"]), "Events": TableDiff()})
    assert text == (
        f"Menus：待译 {len(many)}（{', '.join(many[:REPORT_ID_LIMIT])} 等）；原文改动 1（1）；待复核共 2；废弃 0\n"
        "Events：无变化"
    )


def test_diff_against_game_marks_nothing_for_matching_hashes(game, tmp_path):
    english = read_tables(game.english.read_bytes())
    for table in TABLES:
        save_table(tmp_path, table, {})
    save_table(tmp_path, "Menus", {"248174071668736": item(en_hash("Career"))})
    menus = diff_against_english(english, tmp_path)["Menus"]
    assert menus.changed == [] and menus.obsolete == [] and "248174071668736" not in menus.new
    assert len(menus.new) == len([t for t in english["Menus"].values() if t]) - 1
