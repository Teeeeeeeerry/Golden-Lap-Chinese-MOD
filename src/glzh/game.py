"""玩家本地 Golden Lap 的文件布局。"""

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_APP = Path.home() / "Library/Application Support/Steam/steamapps/common/Golden Lap/goldenlap.app"

TURKISH_BUNDLE = "localization-string-tables-turkish_assets_all.bundle"
ENGLISH_BUNDLE = "localization-string-tables-english_assets_all.bundle"
LOCALES_BUNDLE = "localization-locales_assets_all.bundle"
UI_BUNDLE_GLOB = "ui_assets_all_*.bundle"  # 文件名含内容哈希，随游戏版本变化



def app_path() -> Path:
    """游戏 .app 路径：环境变量 GOLDEN_LAP_APP 优先，否则用 Steam 默认库位置。"""
    return Path(os.environ.get("GOLDEN_LAP_APP", DEFAULT_APP))


@dataclass(frozen=True)
class GameFiles:
    """Addressables 目录（StreamingAssets/aa）下与汉化有关的文件。"""

    aa: Path

    @classmethod
    def from_app(cls, app: Path) -> "GameFiles":
        return cls(Path(app) / "Contents/Resources/Data/StreamingAssets/aa")

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

    def exists(self) -> bool:
        try:
            ui = self.ui
        except FileNotFoundError:
            return False
        return all(path.exists() for path in (self.catalog, self.turkish, self.english, self.locales, ui))
