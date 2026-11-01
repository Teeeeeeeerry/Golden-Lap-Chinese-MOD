"""玩家本地 Golden Lap 的文件布局。"""

from dataclasses import dataclass
from pathlib import Path

TURKISH_BUNDLE = "localization-string-tables-turkish_assets_all.bundle"
ENGLISH_BUNDLE = "localization-string-tables-english_assets_all.bundle"
LOCALES_BUNDLE = "localization-locales_assets_all.bundle"
SHARED_BUNDLE = "localization-assets-shared_assets_all.bundle"  # 各字符串表的共享键
UI_BUNDLE_GLOB = "ui_assets_all_*.bundle"  # 文件名含内容哈希，随游戏版本变化
AA_DIR = "StreamingAssets/aa"  # Addressables 目录，相对 Data 目录


@dataclass(frozen=True)
class GameFiles:
    """游戏 Data 目录下与汉化有关的文件。"""

    data: Path
    build_target: str  # Addressables 目录下资源包所在的目录名，按平台不同
    il2cpp: bool = False  # IL2CPP 打包的游戏没有 Managed 目录

    @property
    def aa(self) -> Path:
        return self.data / AA_DIR

    @property
    def resources(self) -> Path:
        """Resources 目录的序列化文件，自带一套 TMP 字体，不经 catalog 加载。"""
        return self.data / "resources.assets"

    @property
    def race_scene(self) -> Path:
        """比赛场景，排行榜的 20 行状态标签直接存在这里。"""
        return self.data / "level2"

    @property
    def globalgamemanagers(self) -> Path:
        """resources.assets 中脚本引用所在的文件，读取其 MonoBehaviour 时需要。"""
        return self.data / "globalgamemanagers.assets"

    @property
    def managed(self) -> Path:
        """游戏程序集目录，用于为没有内嵌类型信息的文件生成 typetree。"""
        return self.data / "Managed"

    @property
    def bundles(self) -> Path:
        return self.aa / self.build_target

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
    def shared(self) -> Path:
        return self.bundles / SHARED_BUNDLE

    @property
    def ui(self) -> Path:
        matches = sorted(self.bundles.glob(UI_BUNDLE_GLOB))
        if len(matches) != 1:
            raise FileNotFoundError(f"应恰好有一个 {UI_BUNDLE_GLOB}，实际 {len(matches)} 个")
        return matches[0]

    @property
    def inputs(self) -> list[Path]:
        """构建需要读取的原始文件。"""
        return [self.catalog, self.english, self.turkish, self.locales, self.shared, self.ui, self.resources, self.race_scene]

    def exists(self) -> bool:
        """原始文件与只读依赖（globalgamemanagers.assets，以及 Mono 版的程序集）都在。"""
        deps = [self.globalgamemanagers] + ([] if self.il2cpp else [self.managed])
        try:
            return all(path.exists() for path in self.inputs + deps)
        except FileNotFoundError:
            return False
