"""catalog.json：把指定资源包的 CRC 置 0，以及为已有资源包追加登记一个资源。

Addressables 的 catalog 把每个资源包的加载参数（含 m_Crc）序列化在 m_ExtraDataString 中。
被改过的包 CRC 必然不符，Unity 会拒绝加载，所以要把这些包的 m_Crc 改为 0（不校验）。

键、桶、位置条目分别序列化在 m_KeyDataString、m_BucketDataString、m_EntryDataString 中：
第 i 个桶对应第 i 个键，列出该键解析到的条目；条目以下标引用内部 ID、提供者、依赖键（桶）与资源类型。
追加登记只在末尾添加，已有的键、桶、条目及其下标都不变（见 ADR 0005）。
"""

import base64
import hashlib
import json
import re
import struct

# "m_Crc":<数字>，UTF-16LE 编码，字节级匹配以免受奇偶对齐影响
CRC_PATTERN = re.compile(rb'"\x00m\x00_\x00C\x00r\x00c\x00"\x00:\x00((?:[0-9]\x00)+)')
ENTRY = struct.Struct("<7i")  # internalId, provider, dependencyKey, depHash, extraData 偏移, primaryKey, resourceType


def _crc_matches(catalog: dict, extra: bytes) -> dict[str, re.Match]:
    """资源包文件名 → 它在 extra blob 中的 m_Crc 匹配（只在该条目自己的数据段内查找）。"""
    entries = base64.b64decode(catalog["m_EntryDataString"])
    (count,) = struct.unpack_from("<i", entries, 0)
    rows = [ENTRY.unpack_from(entries, 4 + ENTRY.size * i) for i in range(count)]
    starts = sorted({row[4] for row in rows if row[4] >= 0} | {len(extra)})
    found = {}
    for internal_id, _, _, _, data_offset, _, _ in rows:
        path = catalog["m_InternalIds"][internal_id]
        if not path.endswith(".bundle") or data_offset < 0:
            continue
        end = starts[starts.index(data_offset) + 1]
        match = CRC_PATTERN.search(extra, data_offset, end)
        if match:
            found[path.rsplit("/", 1)[-1]] = match
    return found


def disable_crc(catalog_text: str, bundle_names: set[str]) -> str:
    """把 bundle_names 中各包的 m_Crc 改为 0，用空格补齐原长度，使 blob 的长度前缀保持有效。"""
    catalog = json.loads(catalog_text)
    old_b64 = catalog["m_ExtraDataString"]
    extra = bytearray(base64.b64decode(old_b64))
    matches = _crc_matches(catalog, bytes(extra))
    missing = bundle_names - matches.keys()
    if missing:
        raise ValueError(f"catalog 中找不到这些包的 m_Crc：{sorted(missing)}")
    for name in bundle_names:
        digits = matches[name].span(1)
        width = (digits[1] - digits[0]) // 2
        extra[digits[0] : digits[1]] = ("0" + " " * (width - 1)).encode("utf-16-le")
    occurrences = catalog_text.count(old_b64)
    if occurrences != 1:
        # 0 次通常是原文对 base64 中的 / 做了转义
        raise ValueError(f"catalog 文本中 m_ExtraDataString 出现 {occurrences} 次，无法原位替换")
    # 只替换 blob 本身，其余文本原样保留
    return catalog_text.replace(old_b64, base64.b64encode(bytes(extra)).decode())


def bundle_crcs(catalog_text: str) -> dict[str, int]:
    """资源包文件名 → catalog 中记录的 CRC。"""
    catalog = json.loads(catalog_text)
    extra = base64.b64decode(catalog["m_ExtraDataString"])
    return {name: int(m.group(1).decode("utf-16-le")) for name, m in _crc_matches(catalog, extra).items()}


def _key_end(keys: bytes, offset: int) -> int:
    """键数据段中从 offset 开始的一个键的结束位置。只处理 catalog 实际用到的字符串与整数键。"""
    kind = keys[offset]
    if kind in (0, 1):  # ASCII / UTF-16 字符串：长度前缀 + 内容
        (size,) = struct.unpack_from("<i", keys, offset + 1)
        return offset + 5 + size
    if kind == 4:  # Int32
        return offset + 5
    raise ValueError(f"catalog 键数据中有未支持的键类型 {kind}，游戏可能更换了 catalog 格式")


def _key_text(keys: bytes, offset: int):
    end = _key_end(keys, offset)
    kind = keys[offset]
    if kind == 4:
        return struct.unpack_from("<i", keys, offset + 1)[0]
    return keys[offset + 5 : end].decode("ascii" if kind == 0 else "utf-16-le")


def _buckets(blob: bytes) -> list[tuple[int, list[int]]]:
    (count,) = struct.unpack_from("<i", blob, 0)
    out, pos = [], 4
    for _ in range(count):
        offset, size = struct.unpack_from("<ii", blob, pos)
        out.append((offset, list(struct.unpack_from(f"<{size}i", blob, pos + 8))))
        pos += 8 + 4 * size
    return out


def _encode_buckets(buckets: list[tuple[int, list[int]]]) -> bytes:
    out = bytearray(struct.pack("<i", len(buckets)))
    for offset, entries in buckets:
        out += struct.pack(f"<ii{len(entries)}i", offset, len(entries), *entries)
    return bytes(out)


def asset_guid(address: str) -> str:
    """新增资源的 GUID 键：由地址哈希得到，32 位十六进制，与 Unity 资源 GUID 同形。"""
    return hashlib.sha256(f"glzh:{address}".encode()).hexdigest()[:32]


def register_asset(catalog_text: str, *, address: str, internal_id: str, like: str, beside: str, labels: tuple[str, ...]) -> str:
    """为已有资源包追加登记一个资源：键 address 与它的 GUID 解析到新条目，并把条目加进 labels 中的已有标签。

    新条目的提供者、资源类型照抄 like 键的条目（同类资源），依赖照抄 beside 键的条目（同一个包里的资源）。
    """
    catalog = json.loads(catalog_text)
    keys = bytearray(base64.b64decode(catalog["m_KeyDataString"]))
    buckets = _buckets(base64.b64decode(catalog["m_BucketDataString"]))
    entries = bytearray(base64.b64decode(catalog["m_EntryDataString"]))
    index = {_key_text(keys, offset): i for i, (offset, _) in enumerate(buckets)}

    new_keys = (address, asset_guid(address))
    if existing := [k for k in new_keys if k in index]:
        raise ValueError(f"catalog 中已登记 {', '.join(existing)}，游戏可能已自带这项资源")
    missing = [k for k in (like, beside, *labels) if k not in index]
    if missing:
        raise ValueError(f"catalog 中找不到 {', '.join(missing)}，游戏可能更换了资源结构")

    def row(key):  # 该键解析到的第一个条目
        return list(ENTRY.unpack_from(entries, 4 + ENTRY.size * buckets[index[key]][1][0]))

    like_row, beside_row = row(like), row(beside)
    (entry_count,) = struct.unpack_from("<i", entries, 0)
    new_entry = entry_count
    catalog["m_InternalIds"].append(internal_id)
    new_row = like_row.copy()
    new_row[0] = len(catalog["m_InternalIds"]) - 1
    new_row[2], new_row[3] = beside_row[2], beside_row[3]  # 依赖键与依赖哈希：所在的包
    new_row[5] = len(buckets)  # 主键：address
    entries += ENTRY.pack(*new_row)
    struct.pack_into("<i", entries, 0, entry_count + 1)

    for key in new_keys:
        offset = len(keys)
        raw = key.encode("ascii")
        keys += struct.pack("<Bi", 0, len(raw)) + raw
        buckets.append((offset, [new_entry]))
    struct.pack_into("<i", keys, 0, len(buckets))
    for label in labels:
        buckets[index[label]][1].append(new_entry)

    catalog["m_KeyDataString"] = base64.b64encode(bytes(keys)).decode()
    catalog["m_BucketDataString"] = base64.b64encode(_encode_buckets(buckets)).decode()
    catalog["m_EntryDataString"] = base64.b64encode(bytes(entries)).decode()
    # 与原文的书写方式一致（紧凑、不转义非 ASCII），未改动的部分逐字保留
    return json.dumps(catalog, ensure_ascii=False, separators=(",", ":"))
