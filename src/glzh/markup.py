"""译文与英文原文的标记一致性：占位符、富文本标签、字面转义、换行须原样保留。"""

import re
from collections import Counter
from pathlib import Path

from glzh import translations

PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)")  # 只取名字，{x:plural:…} 的各形式由译者按中文改写
TAG = re.compile(r"</?[A-Za-z][^<>]*>")
ESCAPE = re.compile(r"\\\\|\\(?:n|r|t|u[0-9a-fA-F]{4})")  # 文本里字面的 \n、\u2022，由游戏运行时解析
OPTIONAL = {"ordinalSuffix"}  # 英文序数词后缀（st/nd/rd/th），中文不需要


def _compare(label: str, en: Counter, zh: Counter) -> list[str]:
    missing, extra = en - zh, zh - en
    parts = [f"缺少 {' '.join(sorted(missing.elements()))}"] if missing else []
    parts += [f"多出 {' '.join(sorted(extra.elements()))}"] if extra else []
    return [f"{label}：{'；'.join(parts)}"] if parts else []


def markup_errors(english: str, zh: str) -> list[str]:
    en_names = Counter(n for n in PLACEHOLDER.findall(english) if n not in OPTIONAL)
    zh_names = Counter(n for n in PLACEHOLDER.findall(zh) if n not in OPTIONAL)
    errors = _compare("占位符不一致", en_names, zh_names)
    errors += _compare("标签不一致", Counter(TAG.findall(english)), Counter(TAG.findall(zh)))
    escapes = [Counter(e for e in ESCAPE.findall(text) if e != "\\\\") for text in (english, zh)]
    errors += _compare("转义不一致", *escapes)
    en_lines, zh_lines = english.count("\n"), zh.count("\n")
    if en_lines != zh_lines:
        errors.append(f"换行数不一致：英文 {en_lines}，译文 {zh_lines}")
    return errors


def markup_errors_dir(english: dict[str, dict[int, str]], directory: Path = translations.DEFAULT_DIR) -> list[str]:
    """三张表中每条译文与当前英文原文的标记差异，前缀为文件名与 m_Id。

    跳过英文已不存在的条目和 stale 条目：二者由更新比对报出，待复核时一并修正。
    """
    errors = []
    for table in translations.TABLES:
        source = {str(m_id): text for m_id, text in english.get(table, {}).items()}
        for m_id, item in translations.load_table(directory, table).items():
            if m_id in source and item["status"] != "stale":
                errors += [f"{table}.json: {m_id}: {err}" for err in markup_errors(source[m_id], item["zh"])]
    return errors
