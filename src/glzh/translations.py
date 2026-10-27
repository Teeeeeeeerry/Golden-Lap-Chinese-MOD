"""译文数据：三张字符串表各一份 JSON，以 m_Id 字符串为键。

每条翻译条目的值：
    en_hash  英文原文的哈希（不存原文本身）
    zh       简体中文译文
    status   校对状态：mt 机翻 / ok 已校对 / stale 英文原文已变、待复核
"""

import hashlib
import json
import re
from pathlib import Path

TABLES = ("Content", "Menus", "Events")
STATUSES = ("mt", "ok", "stale")
FIELDS = ("en_hash", "zh", "status")
DEFAULT_DIR = Path(__file__).resolve().parents[2] / "translations" / "zh-Hans"

M_ID = re.compile(r"[0-9]+")
EN_HASH = re.compile(r"[0-9a-f]{16}")


def en_hash(text: str) -> str:
    """英文原文的哈希：UTF-8 的 sha256 取前 16 位十六进制。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def validate_item(item) -> list[str]:
    """校验一条译文的值（en_hash/zh/status），返回不带键前缀的错误信息。"""
    if not isinstance(item, dict):
        return ["值必须是对象"]
    errors = []
    for field in FIELDS:
        if field not in item:
            errors.append(f"缺少 {field}")
        elif not isinstance(item[field], str):
            errors.append(f"{field} 必须是字符串")
    for field in item.keys() - set(FIELDS):
        errors.append(f"多余字段 {field}")
    if isinstance(item.get("en_hash"), str) and not EN_HASH.fullmatch(item["en_hash"]):
        errors.append("en_hash 应为 16 位小写十六进制")
    if item.get("zh") == "":
        errors.append("zh 不能为空")
    if isinstance(item.get("status"), str) and item["status"] not in STATUSES:
        errors.append(f"非法 status {item['status']}（应为 {'/'.join(STATUSES)}）")
    return errors


def validate_table(table: dict) -> list[str]:
    """校验一张表的译文数据，返回错误信息列表；为空表示通过。"""
    errors = []
    for key, item in table.items():
        if not M_ID.fullmatch(key):
            errors.append(f"{key}: 键必须是数字 m_Id")
        errors += [f"{key}: {err}" for err in validate_item(item)]
    return errors


def table_path(directory: Path, table: str) -> Path:
    return Path(directory) / f"{table}.json"


def _reject_duplicates(pairs: list) -> dict:
    keys = [k for k, _ in pairs]
    duplicates = sorted({k for k in keys if keys.count(k) > 1})
    if duplicates:
        raise ValueError(f"重复的键：{', '.join(duplicates)}")
    return dict(pairs)


def load_table(directory: Path, table: str) -> dict:
    """读一张表；JSON 中出现重复的 m_Id 时报错，而不是静默保留最后一个。"""
    return json.loads(table_path(directory, table).read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicates)


def save_table(directory: Path, table: str, data: dict) -> None:
    """按 m_Id 数值排序写出，保证 diff 稳定。"""
    ordered = dict(sorted(data.items(), key=lambda kv: int(kv[0])))
    text = json.dumps(ordered, ensure_ascii=False, indent=2) + "\n"
    table_path(directory, table).write_text(text, encoding="utf-8")


def validate_dir(directory: Path = DEFAULT_DIR) -> list[str]:
    """校验目录下三份译文 JSON，错误信息以文件名为前缀。"""
    errors = []
    for table in TABLES:
        name = table_path(directory, table).name
        if not table_path(directory, table).exists():
            errors.append(f"{name}: 文件不存在")
            continue
        try:
            data = load_table(directory, table)
        except ValueError as e:  # JSONDecodeError 也是 ValueError
            errors.append(f"{name}: {e}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{name}: 顶层必须是对象")
            continue
        errors += [f"{name}: {err}" for err in validate_table(data)]
    from glzh import hardcoded  # 函数内导入：hardcoded 在模块顶层依赖本模块

    errors += hardcoded.validate_file(directory)
    return errors
