from glzh.markup import markup_errors, markup_errors_dir
from glzh.translations import TABLES, en_hash, save_table


def test_identical_markup_passes():
    assert markup_errors("Hi {name}!\n<b>x</b>", "你好 {name}！\n<b>x</b>") == []


def test_missing_and_repeated_placeholders_are_reported():
    assert markup_errors("Overtook {driverName}!", "超车成功！") == ["占位符不一致：缺少 driverName"]
    assert markup_errors("{x} and {x}", "只有 {x}") == ["占位符不一致：缺少 x"]


def test_plural_placeholder_is_compared_by_name():
    en = "for the next {weekends:plural:weekend|{} weekends}"
    assert markup_errors(en, "接下来的 {weekends:plural:{} 个周末|{} 个周末}") == []


def test_choose_placeholder_is_compared_by_name():
    zh = "({required_standing:choose(1):第一名|第 {} 名或更好})"
    assert markup_errors("({required_standing} or above)", zh) == []


def test_ordinal_suffix_may_be_dropped():
    assert markup_errors("Driver finishes {position} {ordinalSuffix}.", "车手以第 {position} 名完赛。") == []


def test_rich_text_tags_and_literal_escapes_must_match():
    en = "<indent=5%>\\u2022 Soft</indent>\\n"
    assert markup_errors(en, "\\u2022 软胎</indent><b>") == [
        "标签不一致：缺少 <indent=5%>；多出 <b>",
        "转义不一致：缺少 \\n",
    ]


def test_comparison_signs_and_escaped_backslashes_are_not_markup():
    assert markup_errors("Speed < 5 > 3, C:\\\\new", "速度 < 5 > 3，C:\\\\新") == []


def test_newline_count_must_match():
    assert markup_errors("a\nb", "ab") == ["换行数不一致：英文 1，译文 0"]


def test_markup_errors_dir_skips_stale_and_vanished_items(tmp_path):
    for table in TABLES:
        save_table(tmp_path, table, {})
    save_table(
        tmp_path,
        "Events",
        {
            "1": {"en_hash": en_hash("Hi {a}"), "zh": "你好", "status": "mt"},
            "2": {"en_hash": en_hash("Hi {a}"), "zh": "你好", "status": "stale"},
            "3": {"en_hash": en_hash("Hi {a}"), "zh": "你好", "status": "mt"},
        },
    )
    english = {"Events": {1: "Hi {a}", 2: "Hi {a}"}}
    assert markup_errors_dir(english, tmp_path) == ["Events.json: 1: 占位符不一致：缺少 a"]
