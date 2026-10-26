import base64
import json
from pathlib import Path

import pytest
import UnityPy

import t1_font_spike as spike


def _catalog_with(options: list[dict]) -> str:
    # m_ExtraDataString 内是 UTF-16LE 的 JSON 片段，前后夹杂二进制长度前缀
    blob = b"\x07" + b"\x00\x01".join(json.dumps(o, separators=(",", ":")).encode("utf-16-le") for o in options)
    return json.dumps({"m_ExtraDataString": base64.b64encode(blob).decode(), "other": "español"}, ensure_ascii=False)


def _crcs(catalog_text: str) -> list[int]:
    blob = base64.b64decode(json.loads(catalog_text)["m_ExtraDataString"])
    return [int(m.decode("utf-16-le")) for m in spike.CRC_PATTERN.findall(blob)]


def test_disable_bundle_crc_zeroes_every_crc_without_changing_length():
    original = _catalog_with([{"m_Hash": "a", "m_Crc": 2529693491}, {"m_Hash": "b", "m_Crc": 7}])

    patched = spike.disable_bundle_crc(original)

    assert _crcs(patched) == [0, 0]
    old_blob = base64.b64decode(json.loads(original)["m_ExtraDataString"])
    new_blob = base64.b64decode(json.loads(patched)["m_ExtraDataString"])
    assert len(new_blob) == len(old_blob)
    assert json.loads(patched)["other"] == "español"


# ---- 以下用玩家本地游戏文件读回验证；本机无游戏时跳过 ----

needs_game = pytest.mark.skipif(not spike.default_bundle_dir().is_dir(), reason="本机未安装 Golden Lap")


def _tables(bundle: bytes) -> dict[str, dict[int, str]]:
    env = UnityPy.load(bundle)
    out = {}
    for o in env.objects:
        if o.type.name == "MonoBehaviour":
            t = o.read_typetree()
            out[t["m_Name"]] = {e["m_Id"]: e["m_Localized"] for e in t["m_TableData"]}
    return out


@needs_game
def test_patch_string_table_replaces_only_given_ids():
    original = (spike.default_bundle_dir() / spike.TURKISH_BUNDLE).read_bytes()
    before = _tables(original)

    after = _tables(spike.patch_string_table(original, {248174071668736: "生涯"}))

    assert after["Menus_tr"][248174071668736] == "生涯"
    after["Menus_tr"][248174071668736] = before["Menus_tr"][248174071668736]
    assert after == before


@needs_game
def test_add_cjk_fallback_puts_noto_sc_into_every_ui_font_chain():
    ui = next(spike.default_bundle_dir().glob(spike.UI_BUNDLE_GLOB)).read_bytes()

    env = UnityPy.load(spike.add_cjk_fallback(ui))

    fonts = {}
    for o in env.objects:
        if o.type.name == "MonoBehaviour":
            t = o.read_typetree()
            if "m_FaceInfo" in t:
                fonts[t["m_Name"]] = (o.path_id, [r["m_PathID"] for r in t["m_FallbackFontAssetTable"]])
    noto_id = fonts[spike.CJK_FONT_ASSET][0]
    for name in ("LiberationSans SDF", "Figtree SDF", "Figtree-Bold SDF", "Figtree-BoldItalic SDF"):
        assert noto_id in fonts[name][1], name
    assert fonts[spike.CJK_FONT_ASSET][1] == []
