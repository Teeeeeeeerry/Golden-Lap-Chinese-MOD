"""catalog.json：把指定资源包的 CRC 置 0。

Addressables 的 catalog 把每个资源包的加载参数（含 m_Crc）序列化在 m_ExtraDataString 中。
被改过的包 CRC 必然不符，Unity 会拒绝加载，所以要把这些包的 m_Crc 改为 0（不校验）。
"""

import base64
import json
import re
import struct

# "m_Crc":<数字>，UTF-16LE 编码，字节级匹配以免受奇偶对齐影响
CRC_PATTERN = re.compile(rb'"\x00m\x00_\x00C\x00r\x00c\x00"\x00:\x00((?:[0-9]\x00)+)')
ENTRY = struct.Struct("<7i")  # internalId, provider, dependencyKey, depHash, extraData 偏移, primaryKey, resourceType


def _crc_offsets(catalog: dict, extra: bytes) -> dict[str, re.Match]:
    """资源包文件名 → 它在 extra blob 中的 m_Crc 匹配。"""
    entries = base64.b64decode(catalog["m_EntryDataString"])
    (count,) = struct.unpack_from("<i", entries, 0)
    found = {}
    for i in range(count):
        internal_id, _, _, _, data_offset, _, _ = ENTRY.unpack_from(entries, 4 + ENTRY.size * i)
        path = catalog["m_InternalIds"][internal_id]
        if not path.endswith(".bundle") or data_offset < 0:
            continue
        match = CRC_PATTERN.search(extra, data_offset)
        if match:
            found[path.rsplit("/", 1)[-1]] = match
    return found


def disable_crc(catalog_text: str, bundle_names: set[str]) -> str:
    """把 bundle_names 中各包的 m_Crc 改为 0，用空格补齐原长度，使 blob 的长度前缀保持有效。"""
    catalog = json.loads(catalog_text)
    old_b64 = catalog["m_ExtraDataString"]
    extra = bytearray(base64.b64decode(old_b64))
    offsets = _crc_offsets(catalog, bytes(extra))
    missing = bundle_names - offsets.keys()
    if missing:
        raise ValueError(f"catalog 中找不到这些包的 m_Crc：{sorted(missing)}")
    for name in bundle_names:
        digits = offsets[name].span(1)
        width = (digits[1] - digits[0]) // 2
        extra[digits[0] : digits[1]] = ("0" + " " * (width - 1)).encode("utf-16-le")
    if catalog_text.count(old_b64) != 1:
        raise ValueError("catalog 中 m_ExtraDataString 不唯一")
    # 只替换 blob 本身，其余文本原样保留
    return catalog_text.replace(old_b64, base64.b64encode(bytes(extra)).decode())


def bundle_crcs(catalog_text: str) -> dict[str, int]:
    """资源包文件名 → catalog 中记录的 CRC。"""
    catalog = json.loads(catalog_text)
    extra = base64.b64decode(catalog["m_ExtraDataString"])
    return {name: int(m.group(1).decode("utf-16-le")) for name, m in _crc_offsets(catalog, extra).items()}
