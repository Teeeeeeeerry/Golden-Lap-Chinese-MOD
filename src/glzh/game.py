"""玩家本地 Golden Lap 的文件布局。"""

import os
from dataclasses import dataclass
from pathlib import Path

from glzh.steam import find_app

DEFAULT_APP = Path.home() / "Library/Application Support/Steam/steamapps/common/Golden Lap/goldenlap.app"

TURKISH_BUNDLE = "localization-string-tables-turkish_assets_all.bundle"
ENGLISH_BUNDLE = "localization-string-tables-english_assets_all.bundle"
LOCALES_BUNDLE = "localization-locales_assets_all.bundle"
UI_BUNDLE_GLOB = "ui_assets_all_*.bundle"  # 文件名含内容哈希，随游戏版本变化



def app_path() -> Path:
    """游戏 .app 路径：环境变量 GOLDEN_LAP_APP 优先，其次在各 Steam 库中查找，最后用 Steam 默认库位置。"""
    if "GOLDEN_LAP_APP" in os.environ:
        return Path(os.environ["GOLDEN_LAP_APP"])
    return find_app() or DEFAULT_APP


@dataclass(frozen=True)
class GameFiles:
    """Addressables 目录（StreamingAssets/aa）下与汉化有关的文件。"""

    aa: Path

    @classmethod
    def from_app(cls, app: Path) -> "GameFiles":
        return cls(Path(app) / "Contents/Resources/Data/StreamingAssets/aa")

    @property
    def app(self) -> Path:
        return self.aa.parents[4]  # goldenlap.app/Contents/Resources/Data/StreamingAssets/aa

    @property
    def bundles(self) -> Path:
        return self.aa / "StandaloneOSX"

    @property
    def catalog(self) -> Path:
        return self.aa / "catalog.json"

    @property
    def turkish(self) -> Path:
        return self.bundles / TURKISH_BUNDLE

    @property
    def english(self) -> Path:
        return self.bundles / ENGLISH_BUNDLE

    @property
    def locales(self) -> Path:
        return self.bundles / LOCALES_BUNDLE

    @property
    def ui(self) -> Path:
        matches = sorted(self.bundles.glob(UI_BUNDLE_GLOB))
        if len(matches) != 1:
            raise FileNotFoundError(f"应恰好有一个 {UI_BUNDLE_GLOB}，实际 {len(matches)} 个")
        return matches[0]

    @property
    def inputs(self) -> list[Path]:
        """构建需要读取的原始文件。"""
        return [self.catalog, self.english, self.turkish, self.locales, self.ui]

    def exists(self) -> bool:
        try:
            return all(path.exists() for path in self.inputs)
        except FileNotFoundError:
            return False
