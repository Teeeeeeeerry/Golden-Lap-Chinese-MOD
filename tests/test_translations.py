import json

from glzh.translations import DEFAULT_DIR, TABLES, en_hash, load_table, save_table, validate_dir, validate_table

GOOD = {"248174071668736": {"en_hash": en_hash("Career"), "zh": "生涯", "status": "ok"}}


def item(**overrides):
    return {"248174071668736": {"en_hash": en_hash("Career"), "zh": "生涯", "status": "ok", **overrides}}


def test_valid_table_has_no_errors():
    assert validate_table(GOOD) == []


def test_reports_missing_field():
    data = item()
    del data["248174071668736"]["zh"]
    assert validate_table(data) == ["248174071668736: 缺少 zh"]


def test_reports_illegal_status():
    assert validate_table(item(status="done")) == ["248174071668736: 非法 status done（应为 mt/ok/stale）"]


def test_reports_non_ascii_digit_key():
    assert validate_table({"²": GOOD["248174071668736"]}) == ["²: 键必须是数字 m_Id"]


def test_reports_malformed_en_hash_and_empty_zh():
    assert validate_table(item(en_hash="x", zh="")) == [
        "248174071668736: en_hash 应为 16 位小写十六进制",
        "248174071668736: zh 不能为空",
    ]


def write_tables(directory, **tables):
    for table in TABLES:
        (directory / f"{table}.json").write_text(tables.get(table, "{}"), encoding="utf-8")


def test_validate_dir_reports_missing_table_file(tmp_path):
    write_tables(tmp_path)
    (tmp_path / "Events.json").unlink()
    assert validate_dir(tmp_path) == ["Events.json: 文件不存在"]


def test_validate_dir_prefixes_errors_with_table(tmp_path):
    write_tables(tmp_path, Events=json.dumps(item(status="nope")))
    assert validate_dir(tmp_path) == ["Events.json: 248174071668736: 非法 status nope（应为 mt/ok/stale）"]


def test_validate_dir_reports_duplicate_m_id(tmp_path):
    one = json.dumps(GOOD["248174071668736"])
    write_tables(tmp_path, Menus=f'{{"248174071668736": {one}, "248174071668736": {one}}}')
    assert validate_dir(tmp_path) == ["Menus.json: 重复的键：248174071668736"]


def test_save_table_round_trips_sorted_by_numeric_m_id(tmp_path):
    data = {"20": GOOD["248174071668736"], "3": GOOD["248174071668736"]}
    save_table(tmp_path, "Menus", data)
    assert list(load_table(tmp_path, "Menus")) == ["3", "20"]


def test_shipped_translations_are_valid():
    assert validate_dir(DEFAULT_DIR) == []
