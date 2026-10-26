"""更新比对：游戏更新后，按 m_Id 比对当前英文原文哈希与仓库译文的 en_hash。"""

from dataclasses import dataclass, field
from pathlib import Path

from glzh import translations


@dataclass
class TableDiff:
    """一张字符串表的差异。"""

    new: list[str] = field(default_factory=list)  # 待译：游戏里有、译文里没有
    changed: list[str] = field(default_factory=list)  # 待复核：英文原文变了
    obsolete: list[str] = field(default_factory=list)  # 废弃：译文里有、游戏里已没有


def diff_table(current: dict[str, str], translations: dict[str, dict]) -> tuple[TableDiff, dict[str, dict]]:
    """current：{m_Id: 当前英文原文哈希}。返回差异，以及把改动条目置为 stale 后的译文。"""
    result = TableDiff()
    updated = {}
    for m_id, item in translations.items():
        if m_id not in current:
            result.obsolete.append(m_id)
            updated[m_id] = item
        elif current[m_id] != item["en_hash"]:
            result.changed.append(m_id)
            # 记下新哈希，复核状态由 stale 承载，下次比对不再重复报出
            updated[m_id] = {**item, "en_hash": current[m_id], "status": "stale"}
        else:
            updated[m_id] = item
    result.new = [m_id for m_id in current if m_id not in translations]
    for ids in (result.new, result.changed, result.obsolete):
        ids.sort(key=int)
    return result, updated


def diff_against_english(english: dict[str, dict[int, str]], translations_dir: Path) -> dict[str, tuple[TableDiff, dict]]:
    """以玩家本地英文字符串表为准，比对仓库三张表的译文。英文为空的条目无需翻译，不计入。"""
    out = {}
    for table in translations.TABLES:
        current = {str(m_id): translations.en_hash(text) for m_id, text in english.get(table, {}).items() if text}
        out[table] = diff_table(current, translations.load_table(translations_dir, table))
    return out


def format_report(diffs: dict[str, TableDiff]) -> str:
    lines = []
    for table, d in diffs.items():
        if not (d.new or d.changed or d.obsolete):
            lines.append(f"{table}：无变化")
            continue

        def part(label, ids):
            return f"{label} {len(ids)}" + (f"（{', '.join(ids)}）" if ids else "")

        lines.append(f"{table}：{part('待译', d.new)}；{part('待复核', d.changed)}；{part('废弃', d.obsolete)}")
    return "\n".join(lines)
