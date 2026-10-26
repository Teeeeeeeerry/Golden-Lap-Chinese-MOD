import json
import shutil

import pytest

from glzh.install import MANIFEST, AlreadyPatched, install
from glzh.string_tables import read_tables
from tests.conftest import sha


def test_install_backs_up_originals_patches_game_and_is_repeatable(fake_game, originals, tmp_path):
    backup = tmp_path / "backup"
    written = install(fake_game, backup)
    assert sorted(written) == sorted(originals)
    assert all(sha(backup / rel) == digest for rel, digest in originals.items())
    assert read_tables(fake_game.turkish.read_bytes())["Menus"][248174071668736] == "生涯"
    first = {rel: sha(fake_game.aa / rel) for rel in written}
    assert all(first[rel] != originals[rel] for rel in written)
    assert json.loads((backup / MANIFEST).read_text()) == first

    # 再跑一次：备份仍是原版，写入结果完全一致
    install(fake_game, backup)
    assert all(sha(backup / rel) == digest for rel, digest in originals.items())
    assert {rel: sha(fake_game.aa / rel) for rel in written} == first


def test_install_refreshes_backup_after_game_update(fake_game, game, tmp_path):
    backup = tmp_path / "backup"
    install(fake_game, backup)
    # 模拟游戏更新：catalog 与土耳其语包被新版本覆盖（这里用原版代替，内容与注入后不同即可）
    shutil.copy2(game.catalog, fake_game.catalog)
    shutil.copy2(game.turkish, fake_game.turkish)
    (backup / "StandaloneOSX" / game.turkish.name).write_bytes(b"stale backup")
    install(fake_game, backup)
    assert sha(backup / "StandaloneOSX" / game.turkish.name) == sha(game.turkish)


def test_install_refuses_when_game_is_patched_but_backup_is_gone(fake_game, tmp_path):
    install(fake_game, tmp_path / "backup")
    with pytest.raises(AlreadyPatched, match="验证游戏文件的完整性"):
        install(fake_game, tmp_path / "new-backup")
