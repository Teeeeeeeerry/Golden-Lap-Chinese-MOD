"""更新比对：游戏更新后，按 m_Id 比对当前英文原文哈希与仓库译文的 en_hash。"""

from dataclasses import dataclass, field
from pathlib import Path

from glzh import translations

REPORT_ID_LIMIT = 10  # 报告中每类最多列出的 m_Id 个数


@dataclass
class TableDiff:
    """一张字符串表的比对结果。"""

    new: list[str] = field(default_factory=list)  # 待译：游戏里有、译文里没有
    changed: list[str] = field(default_factory=list)  # 待复核：英文原文变了，本次置为 stale
    obsolete: list[str] = field(default_factory=list)  # 废弃：译文里有、游戏里已没有
    stale: list[str] = field(default_factory=list)  # 比对后仍处于待复核状态的全部条目
    updated: dict[str, dict] = field(default_factory=dict)  # 把改动条目置为 stale 后的译文


def diff_table(current: dict[str, str], items: dict[str, dict], untranslatable: set[str] = frozenset()) -> TableDiff:
    """current：{m_Id: 当前英文原文哈希}；items：仓库中这张表的译文。

    untranslatable 是英文原文为空的 m_Id：无需翻译，不算待译；但已有译文时仍按原文改动处理，而非废弃。
    """
    result = TableDiff()
    for m_id, item in items.items():
        if m_id not in current:
            result.obsolete.append(m_id)
            result.updated[m_id] = item
        elif current[m_id] != item["en_hash"]:
            result.changed.append(m_id)
            # 记下新哈希，复核状态由 stale 承载，下次比对不再重复报出
            result.updated[m_id] = {**item, "en_hash": current[m_id], "status": "stale"}
        else:
            result.updated[m_id] = item
    result.new = [m_id for m_id in current if m_id not in items and m_id not in untranslatable]
    result.stale = [m_id for m_id, item in result.updated.items() if item["status"] == "stale"]
    for ids in (result.new, result.changed, result.obsolete, result.stale):
        ids.sort(key=int)
    return result


def diff_against_english(english: dict[str, dict[int, str]], translations_dir: Path) -> dict[str, TableDiff]:
    """以玩家本地英文字符串表为准，比对仓库三张表的译文。"""
    from glzh.hardcoded import is_injected  # 安装后英文包里会多出注入的条目，不属于游戏原文

    out = {}
    for table in translations.TABLES:
        source = {m_id: text for m_id, text in english.get(table, {}).items() if not is_injected(m_id)}
        current = {str(m_id): translations.en_hash(text) for m_id, text in source.items()}
        empty = {str(m_id) for m_id, text in source.items() if not text}
        out[table] = diff_table(current, translations.load_table(translations_dir, table), empty)
    return out


def _ids(label: str, ids: list[str]) -> str:
    if not ids:
        return f"{label} 0"
    shown = ", ".join(ids[:REPORT_ID_LIMIT]) + (" 等" if len(ids) > REPORT_ID_LIMIT else "")
    return f"{label} {len(ids)}（{shown}）"


def format_report(diffs: dict[str, TableDiff]) -> str:
    """每张表一行：待译、待复核（本次新增的改动条目与全部 stale 数）、废弃。"""
    lines = []
    for table, d in diffs.items():
        if not (d.new or d.changed or d.obsolete or d.stale):
            lines.append(f"{table}：无变化")
            continue
        lines.append(
            f"{table}：{_ids('待译', d.new)}；{_ids('原文改动', d.changed)}；"
            f"待复核共 {len(d.stale)}；{_ids('废弃', d.obsolete)}"
        )
    return "\n".join(lines)
