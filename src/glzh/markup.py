"""译文与英文原文的标记一致性：占位符、富文本标签、字面转义、换行须原样保留。"""

import re
from collections import Counter

PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)")  # 只取名字，{x:plural:…} 的各形式由译者按中文改写
TAG = re.compile(r"<[^<>]+>")
ESCAPE = re.compile(r"\\(?:n|r|t|u[0-9a-fA-F]{4})")  # 文本里字面的 \n、•，由游戏运行时解析
OPTIONAL = {"ordinalSuffix"}  # 英文序数词后缀（st/nd/rd/th），中文不需要


def _diff(label: str, en: Counter, zh: Counter) -> list[str]:
    if en == zh:
        return []
    missing, extra = en - zh, zh - en
    return [f"{label}：" + " ".join(sorted(missing.elements()) + sorted(extra.elements()))]


def markup_errors(english: str, zh: str) -> list[str]:
    errors = []
    en_names, zh_names = set(PLACEHOLDER.findall(english)), set(PLACEHOLDER.findall(zh))
    errors += [f"缺少占位符 {{{name}}}" for name in sorted(en_names - zh_names - OPTIONAL)]
    errors += [f"多出占位符 {{{name}}}" for name in sorted(zh_names - en_names)]
    errors += _diff("标签不一致", Counter(TAG.findall(english)), Counter(TAG.findall(zh)))
    errors += _diff("转义不一致", Counter(ESCAPE.findall(english)), Counter(ESCAPE.findall(zh)))
    if english.count("\n") != zh.count("\n"):
        errors.append(f"换行数不一致：英文 {english.count(chr(10))}，译文 {zh.count(chr(10))}")
    return errors


def table_markup_errors(english: dict[int, str], items: dict[str, dict]) -> list[str]:
    """一张表中每条译文与当前英文原文的标记差异，前缀为 m_Id。英文已不存在的条目由更新比对处理，这里跳过。"""
    errors = []
    for m_id, item in items.items():
        if int(m_id) in english:
            errors += [f"{m_id}: {err}" for err in markup_errors(english[int(m_id)], item["zh"])]
    return errors
