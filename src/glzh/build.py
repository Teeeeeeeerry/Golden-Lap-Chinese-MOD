"""构建：由玩家本地的原始游戏文件与译文生成待写回的文件。"""

from pathlib import Path

import UnityPy

from glzh import catalog, fonts, hardcoded, string_tables, translations
from glzh.bundles import PACKER
from glzh.game import GameFiles

LANGUAGE_CODE = "tr"  # 被顶替的语言选项
LANGUAGE_NAME = "简体中文"
LANGUAGE_CULTURE = "zh-CN"


def build(
    src: GameFiles, translations_dir: Path = translations.DEFAULT_DIR, deps: GameFiles | None = None
) -> dict[str, bytes]:
    """读取 src 中的原始文件，返回 {相对 Data 目录的路径: 新内容}。

    deps 提供读取 resources.assets 所需的只读依赖（程序集与 globalgamemanagers.assets），
    默认取 src 自身；从备份构建时传入真实游戏。
    """
    english = string_tables.read_tables(src.english.read_bytes())
    turkish = string_tables.read_tables(src.turkish.read_bytes())
    data = {table: translations.load_table(translations_dir, table) for table in translations.TABLES}
    texts = {
        table: string_tables.localized_table(english[table], data[table], turkish.get(table, {}))
        for table in translations.TABLES
    }
    hard = hardcoded.load_hardcoded(translations_dir)
    # 只查译文：英文回退原文由原有字体显示，不靠中文字体
    ui = src.ui.read_bytes()
    all_items = [item for table in data.values() for item in table.values()] + list(hard.values())
    chars = fonts.required_chars(item["zh"] for item in all_items)
    fonts.ensure_glyphs(fonts.missing_glyphs(ui, chars))

    # ui 包很大，字体后备与写死文本在同一次加载中处理，只写回一次
    env = UnityPy.load(ui)
    fonts.inject_cjk_fallback(env)
    outputs = {}
    if hard:
        originals = hardcoded.localize_components(env, hard, hardcoded.menus_guid(src.shared.read_bytes()))
        if originals:
            ids = {hardcoded.entry_id(key): key for key in originals}
            texts[hardcoded.TABLE].update({m_id: hard[key]["zh"] for m_id, key in ids.items()})
            outputs[src.shared] = hardcoded.add_shared_entries(src.shared.read_bytes(), originals)
            # 英文行写组件原文：其他语言缺这一行时回退英文，显示与原版一致
            outputs[src.english] = string_tables.patch_string_tables(
                src.english.read_bytes(), {hardcoded.TABLE: {m_id: originals[key] for m_id, key in ids.items()}}
            )
    outputs |= {
        src.ui: env.file.save(packer=PACKER),
        src.resources: fonts.add_cjk_fallback_serialized(src.resources.read_bytes(), deps or src, chars),
        src.turkish: string_tables.patch_string_tables(src.turkish.read_bytes(), texts),
        src.locales: string_tables.rename_language_option(
            src.locales.read_bytes(), LANGUAGE_CODE, LANGUAGE_NAME, LANGUAGE_CULTURE
        ),
    }
    # 只有经 catalog 加载的 Addressables 包需要把 CRC 置 0；resources.assets 不在 catalog 中
    patched = {path.name for path in outputs if path.parent == src.bundles}
    outputs[src.catalog] = catalog.disable_crc(src.catalog.read_text(encoding="utf-8"), patched).encode("utf-8")
    return {path.relative_to(src.data).as_posix(): data for path, data in outputs.items()}
