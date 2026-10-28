from glzh.markup import markup_errors, markup_errors_dir, width_warnings_dir
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


def _width_dir(tmp_path, table, items):
    """把 {m_id: (英文, 译文, 状态)} 写成译文目录，返回英文原文表。"""
    for t in TABLES:
        save_table(tmp_path, t, {})
    save_table(tmp_path, table, {m: {"en_hash": en_hash(en), "zh": zh, "status": st} for m, (en, zh, st) in items.items()})
    return {table: {int(m): en for m, (en, _, _) in items.items()}}


def test_width_warning_lists_much_wider_single_line_translation(tmp_path):
    english = _width_dir(tmp_path, "Menus", {"7": ("({required_standing} or above)", "（需第 {required_standing} 名或更好）", "mt")})
    assert width_warnings_dir(english, tmp_path) == [
        "Menus.json: 7: 译文 20 列，英文 13 列：({required_standing} or above) → （需第 {required_standing} 名或更好）"
    ]


def test_width_warning_skips_short_labels_long_text_and_stale_items(tmp_path):
    english = _width_dir(
        tmp_path,
        "Race UI",
        {
            "1": ("Pit", "进站", "mt"),
            "2": ("Wet", "全雨胎", "mt"),
            "3": ("A line\nB", "很长很长很长很长很长很长的第一行\n第二行", "mt"),
            "4": ("Tip:\\nok", "很长很长很长很长很长很长的提示\\n好", "mt"),
            "5": ("Box", "这条已经过时的译文非常长", "stale"),
            "6": ("", "空", "mt"),
            "7": ("Seven sponsors are watching your every race this season", "七家赞助商" * 9, "mt"),
        },
    )
    assert width_warnings_dir(english, tmp_path) == []


def test_width_counts_placeholders_as_short_values(tmp_path):
    # 按占位符名字的长度算，长名字会把两边都撑宽，比例不到 1.3，这条就漏报了
    english = _width_dir(tmp_path, "Events", {"1": ("{otherDriverFullName} won", "{otherDriverFullName} 赢得比赛", "mt")})
    assert width_warnings_dir(english, tmp_path) == [
        "Events.json: 1: 译文 11 列，英文 6 列：{otherDriverFullName} won → {otherDriverFullName} 赢得比赛"
    ]


def test_width_of_branching_placeholder_is_its_widest_branch(tmp_path):
    english = _width_dir(
        tmp_path,
        "Menus",
        {
            "1": ("{n:plural:{} lap|{} laps} left", "剩余 {n:plural:{} 圈|{} 圈全部跑完的比赛}", "mt"),
            "2": ("({n} or above)", "({n:choose(1):第一名|第 {} 名或更好})", "mt"),
        },
    )
    assert width_warnings_dir(english, tmp_path) == [
        "Menus.json: 1: 译文 24 列，英文 12 列：{n:plural:{} lap|{} laps} left → 剩余 {n:plural:{} 圈|{} 圈全部跑完的比赛}"
    ]


def test_width_counts_chinese_quotes_and_ellipsis_as_full_width_and_stray_braces_as_text(tmp_path):
    english = _width_dir(
        tmp_path,
        "Menus",
        {
            "1": ("Hello", "“你好”……", "mt"),
            "2": ("Pit {", "进站 {还有一大段没有闭合的文字", "mt"),
        },
    )
    assert width_warnings_dir(english, tmp_path) == [
        "Menus.json: 1: 译文 12 列，英文 5 列：Hello → “你好”……",
        "Menus.json: 2: 译文 30 列，英文 5 列：Pit { → 进站 {还有一大段没有闭合的文字",
    ]


def test_width_handles_colons_in_branches_and_literal_escapes(tmp_path):
    english = _width_dir(
        tmp_path,
        "Race UI",
        {
            "1": ("{n:plural:Lap|Laps}", "{n:plural:圈数：{}|圈数：{}，已全部跑完}", "mt"),
            # 英文的 • 显示为一个圆点，按 6 个字符算会让英文偏宽而漏报
            "2": ("\\u2022 Box", "\\u2022 立即进站换胎", "mt"),
        },
    )
    assert width_warnings_dir(english, tmp_path) == [
        "Race UI.json: 1: 译文 20 列，英文 4 列：{n:plural:Lap|Laps} → {n:plural:圈数：{}|圈数：{}，已全部跑完}",
        "Race UI.json: 2: 译文 14 列，英文 5 列：\\u2022 Box → \\u2022 立即进站换胎",
    ]
