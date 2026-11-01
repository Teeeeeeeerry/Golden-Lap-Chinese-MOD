from pathlib import Path

from glzh.steam import APP_ID
from glzh_windows import BUILD_TARGET, DATA_DIR, Windows, game_files


def steam_with_game(tmp_path: Path, installdir: str = "Golden Lap") -> Path:
    """第二个 Steam 库里装着游戏的 Steam 目录。"""
    root, library = tmp_path / "Steam", tmp_path / "SteamLibrary"
    (root / "steamapps").mkdir(parents=True)
    escaped = str(library).replace("\\", "\\\\")  # libraryfolders.vdf 里的路径是转义过的
    (root / "steamapps/libraryfolders.vdf").write_text(f'"libraryfolders" {{ "1" {{ "path" "{escaped}" }} }}')
    (library / "steamapps/common" / installdir / DATA_DIR).mkdir(parents=True)
    (library / f"steamapps/appmanifest_{APP_ID}.acf").write_text(f'"AppState" {{ "installdir" "{installdir}" }}')
    return root


def platform(steam=None, **environ) -> Windows:
    return Windows(steam_path=lambda: steam, environ=environ)


def test_finds_game_in_secondary_library_from_registry(tmp_path):
    root = steam_with_game(tmp_path, "GL Custom")
    assert platform(root).game().data == tmp_path / "SteamLibrary/steamapps/common/GL Custom" / DATA_DIR


def test_golden_lap_dir_wins_over_steam(tmp_path):
    root = steam_with_game(tmp_path)
    assert platform(root, GOLDEN_LAP_DIR=str(tmp_path / "Mine")).game().data == tmp_path / "Mine" / DATA_DIR


def test_falls_back_to_default_location_when_not_found(tmp_path):
    game = platform(tmp_path).game()
    assert game.data == tmp_path / "steamapps/common/Golden Lap" / DATA_DIR
    assert not game.exists()


def test_backup_dir_is_under_local_app_data(tmp_path):
    assert platform(LOCALAPPDATA=str(tmp_path)).backup_dir == tmp_path / "GoldenLapZH/backup"


def test_layout_uses_windows_bundle_directory(tmp_path):
    assert game_files(tmp_path).bundles == tmp_path / DATA_DIR / "StreamingAssets/aa" / BUILD_TARGET


def test_existing_game_does_not_need_managed_assemblies(tmp_path):
    game = game_files(tmp_path)
    game.bundles.mkdir(parents=True)
    for name in ("localization-string-tables-english_assets_all.bundle", "localization-string-tables-turkish_assets_all.bundle",
                 "localization-locales_assets_all.bundle", "localization-assets-shared_assets_all.bundle", "ui_assets_all_abc.bundle"):
        (game.bundles / name).write_bytes(b"")
    for path in (game.catalog, game.resources, game.race_scene, game.globalgamemanagers):
        path.write_bytes(b"")
    assert game.exists()
