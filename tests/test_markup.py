from glzh.markup import markup_errors


def test_identical_markup_passes():
    assert markup_errors("Hi {name}!\n<b>x</b>", "你好 {name}！\n<b>x</b>") == []


def test_missing_placeholder_is_reported():
    assert markup_errors("Overtook {driverName}!", "超车成功！") == ["缺少占位符 {driverName}"]


def test_plural_placeholder_is_compared_by_name():
    en = "for the next {weekends:plural:weekend|{} weekends}"
    assert markup_errors(en, "接下来的 {weekends:plural:{} 个周末|{} 个周末}") == []


def test_ordinal_suffix_may_be_dropped():
    assert markup_errors("Driver finishes {position} {ordinalSuffix}.", "车手以第 {position} 名完赛。") == []


def test_rich_text_tags_and_literal_escapes_must_match():
    en = "<indent=5%>\\u2022 Soft</indent>\\n"
    assert markup_errors(en, "\\u2022 软胎") == ["标签不一致：</indent> <indent=5%>", "转义不一致：\\n"]


def test_newline_count_must_match():
    assert markup_errors("a\nb", "ab") == ["换行数不一致：英文 1，译文 0"]
