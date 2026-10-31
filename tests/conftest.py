import hashlib
import json
import shutil
from pathlib import Path

import pytest

from glzh.game import GameFiles, app_path
from glzh.install import BACKUP_DIR, MANIFEST


def copy_game(src: GameFiles, app: Path, backup_dir: Path | None = None) -> GameFiles:
    """把构建需要的游戏文件拷进 app；backup_dir 中有的文件优先取那里的版本。"""
    files = GameFiles.from_app(app)
    for path in src.inputs + [src.globalgamemanagers]:
        rel = path.relative_to(src.data)
        dst = files.data / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_dir / rel if backup_dir and (backup_dir / rel).exists() else path, dst)
    files.managed.symlink_to(src.managed)  # 只读依赖，不必拷贝
    return files


@pytest.fixture(scope="session")
def game(tmp_path_factory) -> GameFiles:
    """原版游戏文件（只读）；仓库不含游戏资源，找不到游戏时跳过。

    本机装过汉化时，游戏里是注入后的文件，改用安装器备份拼出一份原版副本。
    """
    files = GameFiles.from_app(app_path())
    if not files.exists():
        pytest.skip("未找到本地 Golden Lap，跳过依赖游戏文件的测试")
    manifest = BACKUP_DIR / MANIFEST
    patched = json.loads(manifest.read_text()) if manifest.exists() else {}
    if any((files.data / rel).exists() and sha(files.data / rel) == digest for rel, digest in patched.items()):
        return copy_game(files, tmp_path_factory.mktemp("pristine") / "goldenlap.app", BACKUP_DIR)
    return files


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def fake_game(game, tmp_path):
    """把构建需要的游戏文件拷进临时 .app，避免改动真实游戏。"""
    return copy_game(game, tmp_path / "goldenlap.app")


@pytest.fixture(scope="module")
def originals(game):
    """安装器会改动的文件（相对 Data 目录）→ 原版 sha256。"""
    patched = (game.catalog, game.turkish, game.locales, game.shared, game.english, game.ui, game.resources, game.race_scene)
    return {p.relative_to(game.data).as_posix(): sha(p) for p in patched}
