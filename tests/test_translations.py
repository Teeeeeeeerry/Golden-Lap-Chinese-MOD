import json

from glzh.translations import DEFAULT_DIR, TABLES, en_hash, validate_dir, validate_table

GOOD = {"248174071668736": {"en_hash": en_hash("Career"), "zh": "生涯", "status": "ok"}}


def test_valid_table_has_no_errors():
    assert validate_table(GOOD) == []


def test_reports_missing_key():
    errors = validate_table({"248174071668736": {"en_hash": en_hash("Career"), "status": "mt"}})
    assert len(errors) == 1 and "248174071668736" in errors[0] and "zh" in errors[0]


def test_reports_illegal_status():
    errors = validate_table({"248174071668736": {"en_hash": en_hash("Career"), "zh": "生涯", "status": "done"}})
    assert len(errors) == 1 and "done" in errors[0]


def test_validate_dir_reports_missing_table_file(tmp_path):
    (tmp_path / "Content.json").write_text(json.dumps(GOOD), encoding="utf-8")
    (tmp_path / "Menus.json").write_text("{}", encoding="utf-8")
    assert validate_dir(tmp_path) == ["Events.json: 文件不存在"]


def test_validate_dir_prefixes_errors_with_table(tmp_path):
    bad = {"1": {"en_hash": "x", "zh": "y", "status": "nope"}}
    for table in TABLES:
        (tmp_path / f"{table}.json").write_text(json.dumps(bad if table == "Events" else {}), encoding="utf-8")
    assert validate_dir(tmp_path) == ["Events.json: 1: 非法 status nope（应为 mt/ok/stale）"]


def test_shipped_translations_are_valid():
    assert validate_dir(DEFAULT_DIR) == []
