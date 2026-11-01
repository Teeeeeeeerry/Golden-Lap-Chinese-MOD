"""平台层的接口：核心只通过它接触与系统有关的部分（见 ADR 0010）。"""

from pathlib import Path
from typing import Protocol

from glzh.game import GameFiles


class Platform(Protocol):
    backup_dir: Path  # 原始文件备份与安装记录所在目录
    locate_hint: str  # 找不到游戏时，告诉玩家怎么办

    def game(self) -> GameFiles:
        """本机的游戏文件；找不到时返回默认位置，由调用方用 exists() 判断。"""
        ...

    def preflight(self) -> str | None:
        """改动游戏文件之前的检查：不能继续时返回给玩家看的原因，否则返回 None。"""
        ...
