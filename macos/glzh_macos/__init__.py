"""macOS 平台层：Steam 位置、goldenlap.app 的文件布局与备份目录。"""

import os
from pathlib import Path

from glzh.game import GameFiles
from glzh.steam import find_game

STEAM_ROOT = Path.home() / "Library/Application Support/Steam"
APP_BUNDLE = "goldenlap.app"
DEFAULT_APP = STEAM_ROOT / "steamapps/common/Golden Lap" / APP_BUNDLE
BACKUP_DIR = Path.home() / "Library/Application Support/GoldenLapZH/backup"
BUILD_TARGET = "StandaloneOSX"


def find_app(steam_root: Path = STEAM_ROOT) -> Path | None:
    """在各 Steam 库中查找已安装的 Golden Lap，返回 .app 路径；找不到返回 None。"""
    return find_game(steam_root, APP_BUNDLE)


def app_path() -> Path:
    """游戏 .app 路径：环境变量 GOLDEN_LAP_APP 优先，其次在各 Steam 库中查找，最后用 Steam 默认库位置。"""
    if "GOLDEN_LAP_APP" in os.environ:
        return Path(os.environ["GOLDEN_LAP_APP"])
    return find_app() or DEFAULT_APP


def game_files(app: Path) -> GameFiles:
    """goldenlap.app 里的游戏文件。"""
    return GameFiles(Path(app) / "Contents/Resources/Data", BUILD_TARGET)


class MacOS:
    backup_dir = BACKUP_DIR
    locate_hint = "请确认已在 Steam 中安装，或用环境变量 GOLDEN_LAP_APP 指定 goldenlap.app 的路径。"

    def game(self) -> GameFiles:
        return game_files(app_path())

    def preflight(self) -> str | None:
        return None
