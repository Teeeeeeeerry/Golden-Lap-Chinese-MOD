import json
import shutil

import pytest

from glzh.fonts import CJK_FONT_ASSET, is_injected_serialized
from glzh.install import MANIFEST, AlreadyPatched, install, restore
from glzh.string_tables import read_tables
from tests.conftest import sha
from tests.test_fonts import edit_serialized_font, serialized_fonts

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


def test_upgrade_adds_race_scene_to_existing_backup(fake_game, originals, tmp_path):
    """v0.0.20 及以前不改 level2：备份里没有它，游戏里的就是原版，升级时补进备份，之后仍能还原。"""
    backup = tmp_path / "backup"
    install(fake_game, backup)
    written = dict(json.loads((backup / MANIFEST).read_text()))
    # 还原 level2，拼出旧版本安装后的样子
    shutil.copy2(backup / "level2", fake_game.race_scene)
    (backup / "level2").unlink()
    del written["level2"]
    (backup / MANIFEST).write_text(json.dumps(written))

    install(fake_game, backup)
    assert all(sha(backup / rel) == digest for rel, digest in originals.items())
    assert sha(fake_game.race_scene) != originals["level2"]
    restore(fake_game, backup)
    assert {rel: sha(fake_game.data / rel) for rel in originals} == originals


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


def test_install_reverts_files_it_no_longer_writes(fake_game, originals, tmp_path):
    """写死文本找不到时，英文包与共享键表包不再产出：上次改过的版本应换回原版并移出安装记录。"""
    from glzh.hardcoded import save_hardcoded
    from glzh.translations import DEFAULT_DIR, TABLES, load_table, save_table

    backup, plain = tmp_path / "backup", tmp_path / "plain"
    install(fake_game, backup)
    plain.mkdir()
    for table in TABLES:
        save_table(plain, table, load_table(DEFAULT_DIR, table))
    save_hardcoded(plain, {})
    written = install(fake_game, backup, plain)
    for rel in (f"{AA}/StandaloneOSX/localization-string-tables-english_assets_all.bundle", f"{AA}/StandaloneOSX/localization-assets-shared_assets_all.bundle"):
        assert sha(fake_game.data / rel) == originals[rel]
    restore(fake_game, backup)
    assert {rel: sha(fake_game.data / rel) for rel in originals} == originals


def test_install_upgrades_v0_0_11_resources_assets_to_multi_atlas(fake_game, game, originals, tmp_path):
    """v0.0.11 的 resources.assets 挂了中文后备但没开多图集：不能被当成原版，重跑应从备份重建。"""
    backup = tmp_path / "backup"
    install(fake_game, backup)
    edit_serialized_font(fake_game, CJK_FONT_ASSET, m_IsMultiAtlasTexturesEnabled=0)
    assert is_injected_serialized(fake_game.resources.read_bytes(), fake_game)
    manifest = json.loads((backup / MANIFEST).read_text())
    (backup / MANIFEST).write_text(json.dumps(manifest | {"resources.assets": sha(fake_game.resources)}))

    install(fake_game, backup)
    assert all(sha(backup / rel) == digest for rel, digest in originals.items())
    cjk = next(t for t in serialized_fonts(fake_game.resources.read_bytes(), game).values() if t["m_Name"] == CJK_FONT_ASSET)
    assert cjk["m_IsMultiAtlasTexturesEnabled"] == 1
    restore(fake_game, backup)
    assert {rel: sha(fake_game.data / rel) for rel in originals} == originals
