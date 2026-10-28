"""字符串表与语言选项：读取英文原文、把译文写回土耳其语字符串表包、改语言选项显示名。"""

import copy
import hashlib

import UnityPy

from glzh.bundles import PACKER, mono_behaviours


def _tables(env):
    """遍历包内的字符串表：(对象, typetree, 表集合名)；表名形如 Menus_tr，集合名为 Menus。"""
    for obj, tree in mono_behaviours(env):
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


def _new_path_id(name: str) -> int:
    """新增对象的 path_id：由名字哈希得到，稳定可复现。"""
    return int.from_bytes(hashlib.sha256(f"glzh:{name}".encode()).digest()[:8], "big", signed=True)


def add_table(bundle: bytes, template: bytes, collection: str, code: str) -> tuple[bytes, str]:
    """以 template 包（如英文包）中 collection 表为模板，在 bundle 中新建语言代码为 code 的同名表，返回新包与新表的资源路径。

    两种语言的字符串表包结构相同（同一个 StringTable 脚本、同样以共享键表包为外部引用），
    模板表里的引用在新包中照样有效。新表的行沿用模板，由 patch_string_tables 改写。
    """
    template_env = UnityPy.load(template)
    found = [(o, t) for o, t, name in _tables(template_env) if name == collection]
    if len(found) != 1:
        raise ValueError(f"模板包中应恰好有一张 {collection} 表，实际 {len(found)} 张")
    source, tree = found[0]
    template_bundle = next(o.read_typetree() for o in template_env.objects if o.type.name == "AssetBundle")
    source_path = next(path for path, entry in template_bundle["m_Container"] if entry["asset"]["m_PathID"] == source.path_id)

    env = UnityPy.load(bundle)
    if any(name == collection for _, _, name in _tables(env)):
        raise ValueError(f"包中已有 {collection} 表")
    sibling = next(obj for obj, _, _ in _tables(env))  # 同一个 StringTable 类型，借它的类型信息
    name = f"{collection}_{code}"
    path = source_path.replace(tree["m_Name"], name)  # Assets/Localization/Race UI_en.asset → …/Race UI_tr.asset
    tree["m_Name"] = name
    tree["m_LocaleId"] = {"m_Code": code}
    obj = copy.copy(sibling)
    obj.path_id = _new_path_id(name)
    obj.save_typetree(tree)
    sibling.assets_file.objects[obj.path_id] = obj

    holder = next(o for o in env.objects if o.type.name == "AssetBundle")
    meta = holder.read_typetree()
    preload = meta["m_PreloadTable"]
    # 与模板一致：脚本、表本身、共享键表
    deps = [tree["m_Script"], {"m_FileID": 0, "m_PathID": obj.path_id}, tree["m_SharedData"]]
    meta["m_Container"].append((path, {"preloadIndex": len(preload), "preloadSize": len(deps), "asset": {"m_FileID": 0, "m_PathID": obj.path_id}}))
    meta["m_Container"].sort(key=lambda item: item[0])
    preload.extend(deps)
    holder.save_typetree(meta)
    return env.file.save(packer=PACKER), path


def rename_language_option(bundle: bytes, code: str, display_name: str, culture: str) -> bytes:
    """把 locales 包中语言代码为 code 的语言选项改显示名，并让它按 culture 区域格式化数字与日期。

    语言代码本身不改：catalog 按代码定位字符串表包。
    """
    env = UnityPy.load(bundle)
    found = False
    for obj, tree in mono_behaviours(env):
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
