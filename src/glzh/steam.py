"""定位 Steam 中的 Golden Lap。"""

import re
from pathlib import Path

APP_ID = "2052040"

_PATH = re.compile(r'"path"\s+"((?:[^"\\]|\\.)*)"')
_INSTALLDIR = re.compile(r'"installdir"\s+"((?:[^"\\]|\\.)*)"')


def _unescape(value: str) -> str:
    return value.replace("\\\\", "\\").replace('\\"', '"')


def library_paths(libraryfolders_vdf: str) -> list[Path]:
    """libraryfolders.vdf 中登记的全部 Steam 库路径。"""
    return [Path(_unescape(p)) for p in _PATH.findall(libraryfolders_vdf)]


def find_game(steam_root: Path, entry: str) -> Path | None:
    """在各 Steam 库中查找已安装的 Golden Lap，返回其安装目录下的 entry；找不到返回 None。"""
    vdf = steam_root / "steamapps/libraryfolders.vdf"
    libraries = [steam_root] + (library_paths(vdf.read_text(encoding="utf-8")) if vdf.exists() else [])
    for library in dict.fromkeys(libraries):
        manifest = library / "steamapps" / f"appmanifest_{APP_ID}.acf"
        installdir = "Golden Lap"
        if manifest.exists():
            match = _INSTALLDIR.search(manifest.read_text(encoding="utf-8"))
            installdir = _unescape(match.group(1)) if match else installdir
        found = library / "steamapps/common" / installdir / entry
        if found.is_dir():
            return found
    return None
