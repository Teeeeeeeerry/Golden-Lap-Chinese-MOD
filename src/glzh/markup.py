"""译文与英文原文的标记一致性：占位符、富文本标签、字面转义、换行须原样保留。"""

import re
import unicodedata
from collections import Counter
from pathlib import Path

from glzh import translations

PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)")  # 只取名字，{x:plural:…} 的各形式由译者按中文改写
TAG = re.compile(r"</?[A-Za-z][^<>]*>")
ESCAPE = re.compile(r"\\\\|\\(?:n|r|t|u[0-9a-fA-F]{4})")  # 文本里字面的 \n、\u2022，由游戏运行时解析
OPTIONAL = {"ordinalSuffix"}  # 英文序数词后缀（st/nd/rd/th），中文不需要

# 宽度预警：只比单行短文本，长文本在游戏里自动换行。两个条件同时满足才提示：
# 只多几列的两三字短标签（如 Pit → 进站）实际放得下，比例很高也不提示；按 2026-10 的译文试算，
# 达到阈值的只有超出赛季奖金栏的名次要求一条
MAX_EN_WIDTH = 40
MIN_EXTRA = 4
MIN_RATIO = 1.3


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
    """各表中每条译文与当前英文原文的标记差异，前缀为文件名与 m_Id。

    跳过英文已不存在的条目和 stale 条目：二者由更新比对报出，待复核时一并修正。
    """
    errors = []
    for table in translations.TABLES:
        source = {str(m_id): text for m_id, text in english.get(table, {}).items()}
        for m_id, item in translations.load_table(directory, table).items():
            if m_id in source and item["status"] != "stale":
                errors += [f"{table}.json: {m_id}: {err}" for err in markup_errors(source[m_id], item["zh"])]
    return errors


def _split_top(text: str, sep: str) -> list[str]:
    """按不在花括号内的 sep 切分。"""
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        depth += (ch == "{") - (ch == "}")
        if ch == sep and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    return parts + [text[start:]]


def display_width(text: str) -> int:
    """估算显示宽度：东亚宽字符 2 列，其余 1 列，富文本标签不占宽度。

    占位符代表一个短数字或短名字，按 2 列计；带分支的占位符（如 {n:plural:A|B}、{n:choose(1):A|B}）按最宽的分支计。
    """
    text = TAG.sub("", text)
    width, i = 0, 0
    while i < len(text):
        if text[i] == "{":
            depth, j = 0, i
            while j < len(text):
                depth += (text[j] == "{") - (text[j] == "}")
                if depth == 0:
                    break
                j += 1
            fields = _split_top(text[i + 1 : j], ":")
            width += max(map(display_width, _split_top(fields[-1], "|"))) if len(fields) > 2 else 2
            i = j + 1
        else:
            width += 2 if unicodedata.east_asian_width(text[i]) in "WF" else 1
            i += 1
    return width


def width_warnings_dir(english: dict[str, dict[int, str]], directory: Path = translations.DEFAULT_DIR) -> list[str]:
    """各表中显示宽度明显超过英文的单行短译文，前缀为文件名与 m_Id；只作提示，不算校验错误。

    跳过的条目与标记检查相同，另外跳过英文为空、含换行或长于 MAX_EN_WIDTH 的条目。
    """
    warnings = []
    for table in translations.TABLES:
        source = {str(m_id): text for m_id, text in english.get(table, {}).items()}
        for m_id, item in translations.load_table(directory, table).items():
            en = source.get(m_id, "")
            # 字面的 \n 由游戏运行时解析为换行，与真换行一样算多行
            if not en or item["status"] == "stale" or "\n" in en or "\\n" in en:
                continue
            en_width, zh_width = display_width(en), display_width(item["zh"])
            if en_width <= MAX_EN_WIDTH and zh_width - en_width >= MIN_EXTRA and zh_width > en_width * MIN_RATIO:
                warnings.append(f"{table}.json: {m_id}: 译文 {zh_width} 列，英文 {en_width} 列：{en} → {item['zh']}")
    return warnings
