"""译文数据：三张字符串表各一份 JSON，以 m_Id 字符串为键。

每条翻译条目的值：
    en_hash  英文原文的哈希（不存原文本身）
    zh       简体中文译文
    status   校对状态：mt 机翻 / ok 已校对 / stale 英文原文已变、待复核
"""

import hashlib
import json
from pathlib import Path

TABLES = ("Content", "Menus", "Events")
STATUSES = ("mt", "ok", "stale")
FIELDS = ("en_hash", "zh", "status")
DEFAULT_DIR = Path(__file__).resolve().parents[2] / "translations" / "zh-Hans"


def en_hash(text: str) -> str:
    """英文原文的哈希：UTF-8 的 sha256 取前 16 位十六进制。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def validate_table(table: dict) -> list[str]:
    """校验一张表的译文数据，返回错误信息列表；为空表示通过。"""
    errors = []
    for key, entry in table.items():
        if not key.isdigit():
            errors.append(f"{key}: 键必须是数字 m_Id")
        if not isinstance(entry, dict):
            errors.append(f"{key}: 值必须是对象")
            continue
        for field in FIELDS:
            if field not in entry:
                errors.append(f"{key}: 缺少 {field}")
            elif not isinstance(entry[field], str):
                errors.append(f"{key}: {field} 必须是字符串")
        for field in entry.keys() - set(FIELDS):
            errors.append(f"{key}: 多余字段 {field}")
        if isinstance(entry.get("status"), str) and entry["status"] not in STATUSES:
            errors.append(f"{key}: 非法 status {entry['status']}（应为 {'/'.join(STATUSES)}）")
    return errors


def load_table(directory: Path, table: str) -> dict:
    return json.loads((Path(directory) / f"{table}.json").read_text(encoding="utf-8"))


def save_table(directory: Path, table: str, data: dict) -> None:
    """按 m_Id 数值排序写出，保证 diff 稳定。"""
    ordered = dict(sorted(data.items(), key=lambda kv: int(kv[0])))
    text = json.dumps(ordered, ensure_ascii=False, indent=2) + "\n"
    (Path(directory) / f"{table}.json").write_text(text, encoding="utf-8")


def validate_dir(directory: Path = DEFAULT_DIR) -> list[str]:
    """校验目录下三份译文 JSON，错误信息以文件名为前缀。"""
    errors = []
    for table in TABLES:
        path = Path(directory) / f"{table}.json"
        if not path.exists():
            errors.append(f"{path.name}: 文件不存在")
            continue
        try:
            data = load_table(directory, table)
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}: JSON 解析失败：{e}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{path.name}: 顶层必须是对象")
            continue
        errors += [f"{path.name}: {err}" for err in validate_table(data)]
    return errors
