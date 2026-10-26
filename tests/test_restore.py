import pytest

from glzh.install import MANIFEST, install, restore
from tests.conftest import sha
from tests.test_string_tables import mono_behaviours


def locale_names(game):
    return {t.get("m_LocaleName") for t in mono_behaviours(game.locales.read_bytes()).values()}


def test_restore_puts_originals_back_and_turkish_returns(fake_game, originals, tmp_path):
    backup = tmp_path / "backup"
    install(fake_game, backup)
    assert "简体中文" in locale_names(fake_game)
    restored = restore(fake_game, backup)
    assert sorted(restored) == sorted(originals)
    assert {rel: sha(fake_game.aa / rel) for rel in originals} == originals
    assert "Turkish" in locale_names(fake_game) and "简体中文" not in locale_names(fake_game)
    assert not (backup / MANIFEST).exists()


def test_restore_without_install_record_changes_nothing(fake_game, originals, tmp_path):
    with pytest.raises(FileNotFoundError, match="安装记录"):
        restore(fake_game, tmp_path / "backup")
    assert {rel: sha(fake_game.aa / rel) for rel in originals} == originals


def test_restore_with_missing_backup_changes_nothing(fake_game, tmp_path):
    backup = tmp_path / "backup"
    install(fake_game, backup)
    patched = {p.name: sha(p) for p in fake_game.inputs}
    (backup / "StandaloneOSX" / fake_game.ui.name).unlink()
    with pytest.raises(FileNotFoundError, match="验证游戏文件的完整性"):
        restore(fake_game, backup)
    assert {p.name: sha(p) for p in fake_game.inputs} == patched


def test_restore_skips_files_the_game_has_since_replaced(fake_game, game, tmp_path):
    backup = tmp_path / "backup"
    install(fake_game, backup)
    # 模拟游戏更新：catalog 已被新版本覆盖，不应再用旧备份回退它
    fake_game.catalog.write_text(game.catalog.read_text(encoding="utf-8") + " ", encoding="utf-8")
    updated = sha(fake_game.catalog)
    restored = restore(fake_game, backup)
    assert "catalog.json" not in restored and sha(fake_game.catalog) == updated
    assert sha(fake_game.turkish) == sha(game.turkish)
