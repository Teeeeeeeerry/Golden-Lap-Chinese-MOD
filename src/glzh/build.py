"""构建：由玩家本地的原始游戏文件与译文生成待写回的文件。"""

from pathlib import Path

from glzh import catalog, fonts, string_tables, translations
from glzh.game import GameFiles

LANGUAGE_CODE = "tr"  # 被顶替的语言选项
LANGUAGE_NAME = "简体中文"
LANGUAGE_CULTURE = "zh-CN"


def build(src: GameFiles, translations_dir: Path = translations.DEFAULT_DIR) -> dict[str, bytes]:
    """读取 src 中的原始文件，返回 {相对 aa 目录的路径: 新内容}。"""
    english = string_tables.read_tables(src.english.read_bytes())
    turkish = string_tables.read_tables(src.turkish.read_bytes())
    texts = {
        table: string_tables.localized_table(
            english[table], translations.load_table(translations_dir, table), turkish.get(table, {})
        )
        for table in translations.TABLES
    }
    ui = src.ui.read_bytes()
    missing = fonts.missing_glyphs(ui, fonts.required_chars(text for table in texts.values() for text in table.values()))
    if missing:
        raise ValueError(f"中文字体缺少这些字的字形：{''.join(sorted(missing))}")
    outputs = {
        src.ui: fonts.add_cjk_fallback(ui),
        src.turkish: string_tables.patch_string_tables(src.turkish.read_bytes(), texts),
        src.locales: string_tables.rename_language_option(
            src.locales.read_bytes(), LANGUAGE_CODE, LANGUAGE_NAME, LANGUAGE_CULTURE
        ),
    }
    patched = {path.name for path in outputs}
    outputs[src.catalog] = catalog.disable_crc(src.catalog.read_text(encoding="utf-8"), patched).encode("utf-8")
    return {path.relative_to(src.aa).as_posix(): data for path, data in outputs.items()}
