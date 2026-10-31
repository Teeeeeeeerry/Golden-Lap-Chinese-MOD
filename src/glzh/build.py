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

    deps 提供读取 resources.assets 和 level2 所需的只读依赖（程序集与 globalgamemanagers.assets），
    默认取 src 自身；从备份构建时传入真实游戏。
    """
    english_bundle, turkish_bundle = src.english.read_bytes(), src.turkish.read_bytes()
    english = string_tables.read_tables(english_bundle)
    turkish = string_tables.read_tables(turkish_bundle)
    if missing := [table for table in translations.TABLES if table not in english]:
        raise ValueError(f"英文包中没有这些字符串表：{', '.join(missing)}；游戏可能更换了表结构")
    # 土耳其语包原本没有的表（Race UI）：照英文包新建，稍后在 catalog 中追加登记（见 ADR 0005）
    added = {}
    for table in translations.TABLES:
        if table not in turkish:
            turkish_bundle, added[table] = string_tables.add_table(turkish_bundle, english_bundle, table, LANGUAGE_CODE)
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
    zh_rows, outputs, missing_texts = hardcoded.relink(env, src, hard)
    texts[hardcoded.TABLE].update(zh_rows)
    if missing_texts:
        # 游戏更新后原文变了：组件保持英文，提示维护者更新 Hardcoded.json
        print(f"未在界面中找到这些写死文本，保持英文：{', '.join(missing_texts)}")
    resources, status_font = fonts.add_cjk_fallback_serialized(src.resources.read_bytes(), deps or src, chars)
    outputs |= {
        src.ui: env.file.save(packer=PACKER),
        src.resources: resources,
        src.race_scene: fonts.use_status_font(src.race_scene.read_bytes(), deps or src, status_font),
        src.turkish: string_tables.patch_string_tables(turkish_bundle, texts),
        src.locales: string_tables.rename_language_option(
            src.locales.read_bytes(), LANGUAGE_CODE, LANGUAGE_NAME, LANGUAGE_CULTURE
        ),
    }
    # 只有经 catalog 加载的 Addressables 包需要把 CRC 置 0；resources.assets、level2 不在 catalog 中
    patched = {path.name for path in outputs if path.parent == src.bundles}
    catalog_text = src.catalog.read_text(encoding="utf-8")
    beside = f"Menus_{LANGUAGE_CODE}"  # 土耳其语包里原有的表，新表与它同包
    for table, path in added.items():
        catalog_text = catalog.register_asset(
            catalog_text,
            address=f"{table}_{LANGUAGE_CODE}",
            internal_id=path,
            like=f"{table}_en",
            beside=beside,
            labels=(f"Locale-{LANGUAGE_CODE}",),
        )
    outputs[src.catalog] = catalog.disable_crc(catalog_text, patched).encode("utf-8")
    return {path.relative_to(src.data).as_posix(): data for path, data in outputs.items()}
