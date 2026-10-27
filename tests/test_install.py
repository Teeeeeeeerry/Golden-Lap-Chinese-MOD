import json
import shutil

import pytest

from glzh.install import MANIFEST, AlreadyPatched, install, restore
from glzh.string_tables import read_tables
from tests.conftest import sha

AA = "StreamingAssets/aa"


def test_install_backs_up_originals_patches_game_and_is_repeatable(fake_game, originals, tmp_path):
    backup = tmp_path / "backup"
    written = install(fake_game, backup)
    assert sorted(written) == sorted(originals)
    assert all(sha(backup / rel) == digest for rel, digest in originals.items())
    assert read_tables(fake_game.turkish.read_bytes())["Menus"][248174071668736] == "生涯"
    first = {rel: sha(fake_game.data / rel) for rel in written}
    assert all(first[rel] != originals[rel] for rel in written)
    assert json.loads((backup / MANIFEST).read_text()) == first

    # 再跑一次：备份仍是原版，写入结果完全一致
    install(fake_game, backup)
    assert all(sha(backup / rel) == digest for rel, digest in originals.items())
    assert {rel: sha(fake_game.data / rel) for rel in written} == first


def test_install_refreshes_backup_after_game_update(fake_game, game, tmp_path):
    backup = tmp_path / "backup"
    install(fake_game, backup)
    # 模拟游戏更新：catalog 与土耳其语包被新版本覆盖（这里用原版代替，内容与注入后不同即可）
    shutil.copy2(game.catalog, fake_game.catalog)
    shutil.copy2(game.turkish, fake_game.turkish)
    (backup / AA / "StandaloneOSX" / game.turkish.name).write_bytes(b"stale backup")
    install(fake_game, backup)
    assert sha(backup / AA / "StandaloneOSX" / game.turkish.name) == sha(game.turkish)


def test_install_refuses_when_game_is_patched_but_backup_is_gone(fake_game, tmp_path):
    install(fake_game, tmp_path / "backup")
    with pytest.raises(AlreadyPatched, match="验证游戏文件的完整性"):
        install(fake_game, tmp_path / "new-backup")


def test_install_refuses_when_resources_assets_is_patched_but_backup_is_gone(fake_game, game, tmp_path):
    install(fake_game, tmp_path / "backup")
    shutil.copy2(game.catalog, fake_game.catalog)  # catalog 看似原版，但 resources.assets 仍是注入后的
    with pytest.raises(AlreadyPatched, match="验证游戏文件的完整性"):
        install(fake_game, tmp_path / "new-backup")


def test_install_migrates_backup_from_v0_0_9_layout(fake_game, game, originals, tmp_path):
    """v0.0.9 的备份与安装记录以 aa 目录为根，且不含 resources.assets。"""
    backup = tmp_path / "backup"
    install(fake_game, backup)
    shutil.copy2(game.resources, fake_game.resources)  # v0.0.9 不改 resources.assets
    aa = backup / "StreamingAssets/aa"
    for path in list(aa.rglob("*")):
        if path.is_file():
            dst = backup / path.relative_to(aa)
            dst.parent.mkdir(parents=True, exist_ok=True)
            path.rename(dst)
    shutil.rmtree(backup / "StreamingAssets")
    (backup / "resources.assets").unlink()
    old = json.loads((backup / MANIFEST).read_text())
    old = {rel.removeprefix("StreamingAssets/aa/"): digest for rel, digest in old.items() if rel != "resources.assets"}
    (backup / MANIFEST).write_text(json.dumps(old))

    install(fake_game, backup)
    assert all(sha(backup / rel) == digest for rel, digest in originals.items())
    restore(fake_game, backup)
    assert {rel: sha(fake_game.data / rel) for rel in originals} == originals


def test_migration_finishes_after_being_interrupted(fake_game, originals, tmp_path):
    """迁移中断在「文件已移动、安装记录仍是旧键」时，重跑也应完成。"""
    backup = tmp_path / "backup"
    install(fake_game, backup)
    patched = json.loads((backup / MANIFEST).read_text())
    (backup / MANIFEST).write_text(json.dumps({rel.removeprefix(f"{AA}/"): d for rel, d in patched.items()}))
    assert install(fake_game, backup)
    assert all(sha(backup / rel) == digest for rel, digest in originals.items())
