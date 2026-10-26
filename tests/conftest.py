import os
from pathlib import Path

import pytest

from glzh.game import DEFAULT_APP, GameFiles


@pytest.fixture(scope="session")
def game() -> GameFiles:
    """玩家本地的游戏文件（只读）；仓库不含游戏资源，找不到游戏时跳过。"""
    files = GameFiles.from_app(Path(os.environ.get("GOLDEN_LAP_APP", DEFAULT_APP)))
    if not files.exists():
        pytest.skip("未找到本地 Golden Lap，跳过依赖游戏文件的测试")
    return files
