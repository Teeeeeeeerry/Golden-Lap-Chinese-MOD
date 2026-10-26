import pytest

from glzh.game import GameFiles, app_path


@pytest.fixture(scope="session")
def game() -> GameFiles:
    """玩家本地的游戏文件（只读）；仓库不含游戏资源，找不到游戏时跳过。"""
    files = GameFiles.from_app(app_path())
    if not files.exists():
        pytest.skip("未找到本地 Golden Lap，跳过依赖游戏文件的测试")
    return files
