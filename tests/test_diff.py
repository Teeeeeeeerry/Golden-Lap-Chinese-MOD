from glzh.diff import diff_table


def item(en_hash, status="ok"):
    return {"en_hash": en_hash, "zh": "译文", "status": status}


def test_new_m_id_is_reported_as_untranslated():
    report, _ = diff_table({"1": "aaaaaaaaaaaaaaaa", "2": "bbbbbbbbbbbbbbbb"}, {"1": item("aaaaaaaaaaaaaaaa")})
    assert (report.new, report.changed, report.obsolete) == (["2"], [], [])


def test_changed_source_is_reported_and_marked_stale():
    report, updated = diff_table({"1": "cccccccccccccccc"}, {"1": item("aaaaaaaaaaaaaaaa")})
    assert (report.new, report.changed, report.obsolete) == ([], ["1"], [])
    # 记下新哈希、置 stale：译文保留待复核，下次比对不再重复报出
    assert updated["1"] == {"en_hash": "cccccccccccccccc", "zh": "译文", "status": "stale"}


def test_vanished_m_id_is_reported_as_obsolete_and_kept():
    report, updated = diff_table({}, {"1": item("aaaaaaaaaaaaaaaa")})
    assert (report.new, report.changed, report.obsolete) == ([], [], ["1"])
    assert updated == {"1": item("aaaaaaaaaaaaaaaa")}


def test_lists_are_sorted_by_numeric_m_id():
    report, _ = diff_table({"10": "a" * 16, "9": "a" * 16}, {})
    assert report.new == ["9", "10"]


def test_format_report_summarises_each_table():
    from glzh.diff import TableDiff, format_report

    text = format_report({"Menus": TableDiff(new=["2"], changed=["1"]), "Events": TableDiff()})
    assert text == "Menus：待译 1（2）；待复核 1（1）；废弃 0\nEvents：无变化"


def test_diff_against_game_marks_nothing_for_matching_hashes(game, tmp_path):
    from glzh.diff import diff_against_english
    from glzh.string_tables import read_tables
    from glzh.translations import TABLES, en_hash, save_table

    english = read_tables(game.english.read_bytes())
    for table in TABLES:
        save_table(tmp_path, table, {})
    save_table(tmp_path, "Menus", {"248174071668736": {"en_hash": en_hash("Career"), "zh": "生涯", "status": "ok"}})
    diffs = diff_against_english(english, tmp_path)
    menus, updated = diffs["Menus"]
    assert menus.changed == [] and menus.obsolete == [] and "248174071668736" not in menus.new
    assert len(menus.new) == len([t for t in english["Menus"].values() if t]) - 1
    assert updated["248174071668736"]["status"] == "ok"
