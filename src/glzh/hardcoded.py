"""写死在界面里的文本：游戏直接写在 ui 包文本组件上、没有引用字符串表的界面文本（如主菜单的「our new game」）。

直接改组件文字会让所有语言都显示中文。改为在 Menus 表新增一个翻译条目：英文行写原文、
土耳其语（简体中文）行写译文，再把组件的本地化引用指向它。其他语言缺这一行时回退英文，显示不变。

译文存于 Hardcoded.json：键是语义键（如 main_menu/our_new_game），值与字符串表译文相同
（en_hash/zh/status）。组件按原文哈希定位，仓库不存英文原文。
"""

import hashlib
import json
import re
from pathlib import Path

import UnityPy

from glzh import string_tables, translations
from glzh.bundles import PACKER, mono_behaviours
from glzh.game import GameFiles

FILE = "Hardcoded.json"
TABLE = "Menus"  # 新增条目所在的字符串表
KEY = re.compile(r"[a-z][a-z0-9_]*(/[a-z0-9_]+)*")  # 以字母开头，避免与数字 m_Id 混淆
INJECTED_FLOOR = 1 << 62  # 注入条目的 m_Id 都不小于它；游戏自身的 m_Id 远小于此


def entry_id(key: str) -> int:
    """语义键 → 新增翻译条目的 m_Id：稳定、落在保留区间内，不与游戏自身的条目冲突。"""
    digest = int.from_bytes(hashlib.sha256(f"glzh:{key}".encode()).digest()[:8], "big")
    return INJECTED_FLOOR + digest % INJECTED_FLOOR


def is_injected(m_id: int) -> bool:
    """m_Id 是否为本项目注入的条目（安装后会出现在英文包里，不属于游戏原文）。"""
    return m_id >= INJECTED_FLOOR


def validate_hardcoded(items: dict) -> list[str]:
    errors = []
    for key, item in items.items():
        if not KEY.fullmatch(key):
            errors.append(f"{key}: 键必须是以小写字母开头、由小写字母、数字、下划线与 / 组成的语义键")
        errors += [f"{key}: {err}" for err in translations.validate_item(item)]
    hashes = [item.get("en_hash") for item in items.values() if isinstance(item, dict)]
    errors += [f"en_hash {h} 重复：同一原文只能对应一条译文" for h in sorted({h for h in hashes if hashes.count(h) > 1})]
    return errors


def validate_file(directory: Path) -> list[str]:
    """校验目录下的 Hardcoded.json（不存在视为空），错误信息以文件名为前缀。"""
    try:
        items = load_hardcoded(directory)
    except ValueError as e:  # JSON 解析失败或重复键
        return [f"{FILE}: {e}"]
    if not isinstance(items, dict):
        return [f"{FILE}: 顶层必须是对象"]
    return [f"{FILE}: {err}" for err in validate_hardcoded(items)]


def load_hardcoded(directory: Path) -> dict:
    """读 Hardcoded.json；不存在时视为没有写死文本的译文。"""
    if not (Path(directory) / FILE).exists():
        return {}
    return translations.load_table(directory, FILE.removesuffix(".json"))


def save_hardcoded(directory: Path, items: dict) -> None:
    """按语义键排序写出，保证 diff 稳定。"""
    text = json.dumps(dict(sorted(items.items())), ensure_ascii=False, indent=2) + "\n"
    (Path(directory) / FILE).write_text(text, encoding="utf-8")


def menus_guid(shared: bytes) -> str:
    """共享键表包中 Menus 表的 GUID，组件按它引用表。"""
    for _, tree in mono_behaviours(UnityPy.load(shared)):
        if tree.get("m_TableCollectionName") == TABLE:
            return tree["m_TableCollectionNameGuidString"]
    raise ValueError(f"共享键表中没有 {TABLE} 表")


def localize_components(env, items: dict, guid: str) -> dict[str, str]:
    """在已加载的 ui 包中，把原文哈希命中译文的写死文本组件改为引用新增条目。

    返回 {语义键: 组件原文}；游戏更新后原文变了、找不到组件的条目跳过。
    """
    by_hash = {item["en_hash"]: key for key, item in items.items()}
    originals = {}
    for obj, tree in mono_behaviours(env):
        ref = tree.get("textLocalization")
        entry = ref and ref["m_TableEntryReference"]
        if ref is None or entry["m_KeyId"] or entry["m_Key"] or ref["m_TableReference"]["m_TableCollectionName"]:
            continue  # 不是文本组件，或已按 id 或名称引用字符串表
        key = by_hash.get(translations.en_hash(tree["m_text"]))
        if key is None:
            continue
        ref["m_TableReference"]["m_TableCollectionName"] = f"GUID:{guid}"
        ref["m_TableEntryReference"]["m_KeyId"] = entry_id(key)
        obj.save_typetree(tree)
        originals[key] = tree["m_text"]
    return originals


def add_shared_entries(shared: bytes, keys: set[str]) -> bytes:
    """在共享键表的 Menus 表中登记新增条目（已有则跳过）。"""
    env = UnityPy.load(shared)
    for obj, tree in mono_behaviours(env):
        if tree.get("m_TableCollectionName") != TABLE:
            continue
        existing = {entry["m_Id"] for entry in tree["m_Entries"]}
        for key in sorted(keys):
            if entry_id(key) not in existing:
                tree["m_Entries"].append({"m_Id": entry_id(key), "m_Key": f"glzh/{key}", "m_Metadata": {"m_Items": []}})
        obj.save_typetree(tree)
    return env.file.save(packer=PACKER)


def relink(env, src: GameFiles, items: dict) -> tuple[dict[int, str], dict, list[str]]:
    """在已加载的 ui 包中处理写死文本。

    返回 (要并入土耳其语 Menus 表的 {m_Id: 译文}, 额外写回的 {路径: 内容}, 未找到组件的语义键)。
    额外写回的是登记了新条目的共享键表包，以及英文行写原文的英文字符串表包。
    """
    if not items:
        return {}, {}, []
    shared = src.shared.read_bytes()
    originals = localize_components(env, items, menus_guid(shared))
    missing = sorted(items.keys() - originals.keys())
    if not originals:
        return {}, {}, missing
    english_rows = {entry_id(key): text for key, text in originals.items()}
    outputs = {
        src.shared: add_shared_entries(shared, set(originals)),
        # 其他语言缺这一行时回退英文，显示与原版一致
        src.english: string_tables.patch_string_tables(src.english.read_bytes(), {TABLE: english_rows}),
    }
    return {entry_id(key): items[key]["zh"] for key in originals}, outputs, missing
