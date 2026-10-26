"""字符串表与语言选项：读取英文原文、把译文写回土耳其语字符串表包、改语言选项显示名。"""

import UnityPy

# 写回时必须压缩，否则 UnityPy 默认输出未压缩的包
PACKER = "lz4"


def _mono_behaviours(env):
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            yield obj, obj.read_typetree()


def _tables(env):
    """遍历包内的字符串表：(对象, typetree, 表集合名)；表名形如 Menus_tr，集合名为 Menus。"""
    for obj, tree in _mono_behaviours(env):
        if "m_TableData" in tree:
            yield obj, tree, tree["m_Name"].rsplit("_", 1)[0]


def read_tables(bundle: bytes) -> dict[str, dict[int, str]]:
    """字符串表包 → {表集合名: {m_Id: 文本}}。"""
    env = UnityPy.load(bundle)
    return {name: {row["m_Id"]: row["m_Localized"] for row in tree["m_TableData"]} for _, tree, name in _tables(env)}


def localized_table(english: dict[int, str], translations: dict[str, dict], turkish_ids=()) -> dict[int, str]:
    """一张表最终写入的文本：有译文用译文，否则用英文原文；英文没有的土耳其语行清空，避免残留土耳其语。

    不核对 en_hash：原文变了的旧译文照常写入，由更新比对报告提示复核。
    """
    out = {m_id: "" for m_id in turkish_ids if m_id not in english}
    for m_id, text in english.items():
        item = translations.get(str(m_id))
        out[m_id] = item["zh"] if item and item["zh"] else text
    return out


def patch_string_tables(bundle: bytes, texts: dict[str, dict[int, str]]) -> bytes:
    """按 m_Id 把文本写回字符串表；表中没有的 m_Id 追加为新行。"""
    env = UnityPy.load(bundle)
    for obj, tree, name in _tables(env):
        if name not in texts:
            continue
        pending = dict(texts[name])
        for row in tree["m_TableData"]:
            if row["m_Id"] in pending:
                row["m_Localized"] = pending.pop(row["m_Id"])
        for m_id, text in pending.items():
            tree["m_TableData"].append({"m_Id": m_id, "m_Localized": text, "m_Metadata": {"m_Items": []}})
        obj.save_typetree(tree)
    return env.file.save(packer=PACKER)


def rename_language_option(bundle: bytes, code: str, display_name: str, culture: str) -> bytes:
    """把 locales 包中语言代码为 code 的语言选项改显示名，并让它按 culture 区域格式化数字与日期。

    语言代码本身不改：catalog 按代码定位字符串表包。
    """
    env = UnityPy.load(bundle)
    found = False
    for obj, tree in _mono_behaviours(env):
        if tree.get("m_Identifier", {}).get("m_Code") != code or "m_LocaleName" not in tree:
            continue
        tree["m_LocaleName"] = display_name
        tree["m_CustomFormatCultureCode"] = culture
        tree["m_UseCustomFormatter"] = 1
        obj.save_typetree(tree)
        found = True
    if not found:
        raise ValueError(f"locales 包中没有语言代码 {code}")
    return env.file.save(packer=PACKER)
