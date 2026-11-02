"""Windows 平台层：从注册表找 Steam、goldenlap_Data 的文件布局与备份目录。"""

import os
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path

from glzh.game import GameFiles
from glzh.steam import find_game

DATA_DIR = "goldenlap_Data"
BUILD_TARGET = "StandaloneWindows64"
DEFAULT_STEAM = Path(r"C:\Program Files (x86)\Steam")
STEAM_KEY = r"Software\Valve\Steam"
GAME_EXE = "goldenlap.exe"


def registry_steam_path() -> Path | None:
    """注册表里登记的 Steam 安装目录；没有登记时返回 None。"""
    import winreg  # 只有 Windows 才有这个模块

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STEAM_KEY) as key:
            return Path(winreg.QueryValueEx(key, "SteamPath")[0])
    except OSError:
        return None


def game_is_running() -> bool:
    """任务列表里有没有游戏进程；查不了时当作没有，写入时的占用错误会兜底。"""
    try:
        listed = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {GAME_EXE}", "/NH"], capture_output=True, text=True, errors="replace", timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return GAME_EXE in listed.stdout.lower()


def game_files(game_dir: Path) -> GameFiles:
    """游戏安装目录里的游戏文件。"""
    return GameFiles(Path(game_dir) / DATA_DIR, BUILD_TARGET, il2cpp=True)


class Windows:
    locate_hint = "请确认已在 Steam 中安装，或用环境变量 GOLDEN_LAP_DIR 指定游戏目录（goldenlap.exe 所在的文件夹）。"

    def __init__(
        self,
        steam_path: Callable[[], Path | None] = registry_steam_path,
        environ: Mapping[str, str] = os.environ,
        running: Callable[[], bool] = game_is_running,
    ):
        self.steam_path, self.environ, self.running = steam_path, environ, running

    @property
    def backup_dir(self) -> Path:
        local = self.environ.get("LOCALAPPDATA")
        return (Path(local) if local else Path.home() / "AppData/Local") / "GoldenLapZH/backup"

    def game(self) -> GameFiles:
        """环境变量 GOLDEN_LAP_DIR 优先，其次在各 Steam 库中查找，最后用 Steam 默认库位置。"""
        if "GOLDEN_LAP_DIR" in self.environ:
            return game_files(Path(self.environ["GOLDEN_LAP_DIR"]))
        steam = self.steam_path() or DEFAULT_STEAM
        data = find_game(steam, DATA_DIR)
        return game_files(data.parent if data else steam / "steamapps/common/Golden Lap")

    def preflight(self) -> str | None:
        return "Golden Lap 正在运行，请先退出游戏再运行。游戏文件没有改动。" if self.running() else None
