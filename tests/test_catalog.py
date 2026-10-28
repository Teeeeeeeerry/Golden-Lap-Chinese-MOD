import base64
import json
import struct

import pytest

from glzh.catalog import bundle_crcs, disable_crc
from glzh.game import LOCALES_BUNDLE, TURKISH_BUNDLE


def test_disable_crc_zeroes_only_named_bundles(game):
    text = game.catalog.read_text(encoding="utf-8")
    before = bundle_crcs(text)
    after = bundle_crcs(disable_crc(text, {TURKISH_BUNDLE, LOCALES_BUNDLE}))
    assert after[TURKISH_BUNDLE] == 0 and after[LOCALES_BUNDLE] == 0
    others = before.keys() - {TURKISH_BUNDLE, LOCALES_BUNDLE}
    assert len(others) > 10 and all(after[name] == before[name] != 0 for name in others)


def test_disable_crc_keeps_catalog_length(game):
    text = game.catalog.read_text(encoding="utf-8")
    assert len(disable_crc(text, {TURKISH_BUNDLE})) == len(text)


def test_disable_crc_rejects_unknown_bundle(game):
    with pytest.raises(ValueError, match="nope.bundle"):
        disable_crc(game.catalog.read_text(encoding="utf-8"), {"nope.bundle"})


def resolve(catalog_text: str) -> dict:
    """独立于实现读 catalog：键 → 它解析到的位置列表（内部 ID、提供者、类型、依赖包的内部 ID）。"""
    catalog = json.loads(catalog_text)
    keys_blob = base64.b64decode(catalog["m_KeyDataString"])
    buckets_blob = base64.b64decode(catalog["m_BucketDataString"])
    entries_blob = base64.b64decode(catalog["m_EntryDataString"])

    def key_at(offset):
        kind = keys_blob[offset]
        if kind in (0, 1):
            (size,) = struct.unpack_from("<i", keys_blob, offset + 1)
            return keys_blob[offset + 5 : offset + 5 + size].decode("ascii" if kind == 0 else "utf-16-le")
        if kind == 4:
            return struct.unpack_from("<i", keys_blob, offset + 1)[0]
        raise AssertionError(f"未处理的键类型 {kind}")

    (count,) = struct.unpack_from("<i", buckets_blob, 0)
    buckets, pos = [], 4
    for _ in range(count):
        offset, size = struct.unpack_from("<ii", buckets_blob, pos)
        buckets.append((key_at(offset), struct.unpack_from(f"<{size}i", buckets_blob, pos + 8)))
        pos += 8 + 4 * size
    (count,) = struct.unpack_from("<i", entries_blob, 0)
    rows = [struct.unpack_from("<7i", entries_blob, 4 + 28 * i) for i in range(count)]

    def location(index):
        internal_id, provider, dependency, _, _, _, resource_type = rows[index]
        deps = tuple(catalog["m_InternalIds"][rows[e][0]] for e in buckets[dependency][1]) if dependency >= 0 else ()
        return {
            "internal_id": catalog["m_InternalIds"][internal_id],
            "provider": catalog["m_ProviderIds"][provider],
            "type": catalog["m_resourceTypes"][resource_type]["m_ClassName"],
            "dependencies": deps,
        }

    return {key: [location(e) for e in entries] for key, entries in buckets}
