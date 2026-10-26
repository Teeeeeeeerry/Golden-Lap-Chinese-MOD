"""构建：由玩家本地的原始游戏文件与译文生成待写回的文件。"""

from glzh import catalog, string_tables, translations
from glzh.game import GameFiles

LOCALE_CODE = "tr"  # 被顶替的语言选项
LOCALE_NAME = "简体中文"
LOCALE_CULTURE = "zh-CN"


def build(src: GameFiles, translations_dir=translations.DEFAULT_DIR) -> dict[str, bytes]:
    """读取 src 中的原始文件，返回 {相对 aa 目录的路径: 新内容}。"""
    english = string_tables.read_tables(src.english.read_bytes())
    texts = {
        table: string_tables.localized_table(english[table], translations.load_table(translations_dir, table))
        for table in translations.TABLES
    }
    outputs = {
        src.turkish: string_tables.patch_string_tables(src.turkish.read_bytes(), texts),
        src.locales: string_tables.rename_locale(src.locales.read_bytes(), LOCALE_CODE, LOCALE_NAME, LOCALE_CULTURE),
    }
    patched = {path.name for path in outputs}
    outputs[src.catalog] = catalog.disable_crc(src.catalog.read_text(encoding="utf-8"), patched).encode("utf-8")
    return {path.relative_to(src.aa).as_posix(): data for path, data in outputs.items()}
