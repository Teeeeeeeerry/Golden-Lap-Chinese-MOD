import hashlib
import shutil

import pytest

from glzh.game import GameFiles, app_path


@pytest.fixture(scope="session")
def game() -> GameFiles:
    """玩家本地的游戏文件（只读）；仓库不含游戏资源，找不到游戏时跳过。"""
    files = GameFiles.from_app(app_path())
    if not files.exists():
        pytest.skip("未找到本地 Golden Lap，跳过依赖游戏文件的测试")
    return files


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def fake_game(game, tmp_path):
    """把构建需要的游戏文件拷进临时 .app，避免改动真实游戏。"""
    files = GameFiles.from_app(tmp_path / "goldenlap.app")
    for src in game.inputs:
        dst = files.aa / src.relative_to(game.aa)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return files


@pytest.fixture(scope="module")
def originals(game):
    return {p.relative_to(game.aa).as_posix(): sha(p) for p in (game.catalog, game.turkish, game.locales, game.ui)}
