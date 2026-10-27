import json

from glzh.hardcoded import entry_id, load_hardcoded, save_hardcoded, validate_hardcoded
from glzh.string_tables import read_tables
from glzh.translations import DEFAULT_DIR, en_hash, validate_dir

ITEM = {"en_hash": en_hash("our new game"), "zh": "我们的新游戏", "status": "mt"}


def test_valid_hardcoded_items_use_slug_keys():
    assert validate_hardcoded({"main_menu/our_new_game": ITEM}) == []
    assert validate_hardcoded({"123": ITEM}) == ["123: 键必须是以小写字母开头、由小写字母、数字、下划线与 / 组成的语义键"]


def test_entry_id_is_stable_and_does_not_clash_with_game_ids(game):
    assert entry_id("main_menu/our_new_game") == entry_id("main_menu/our_new_game")
    assert entry_id("main_menu/our_new_game") != entry_id("main_menu/other")
    english = read_tables(game.english.read_bytes())
    assert all(entry_id("main_menu/our_new_game") not in rows for rows in english.values())


def test_save_and_load_round_trip_sorted_by_key(tmp_path):
    save_hardcoded(tmp_path, {"b/x": ITEM, "a/y": ITEM})
    assert list(load_hardcoded(tmp_path)) == ["a/y", "b/x"]
    assert list(json.loads((tmp_path / "Hardcoded.json").read_text(encoding="utf-8"))) == ["a/y", "b/x"]


def test_shipped_hardcoded_translations_are_valid():
    assert validate_dir(DEFAULT_DIR) == []
    assert "main_menu/our_new_game" in load_hardcoded(DEFAULT_DIR)
