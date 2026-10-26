"""T1 字体渲染最小验证（spike）。

就地修改玩家本地的 Golden Lap：
1. 把游戏自带的思源黑体动态字体 `NotoSansSC-Black SDF` 挂到 ui_assets_all 包内每个 TMP 字体的后备链末尾；
2. 把土耳其语 Menus 表中若干条替换为简体中文；
3. 把 catalog.json 中各资源包的 CRC 置 0，否则改过的包因 CRC 不符而加载失败。

用法：
    python t1_font_spike.py apply     # 备份原文件后注入
    python t1_font_spike.py restore   # 从备份还原
"""

import base64
import json
import re
import shutil
import sys
from pathlib import Path

import UnityPy

GAME_DIR = Path.home() / "Library/Application Support/Steam/steamapps/common/Golden Lap/goldenlap.app"
TURKISH_BUNDLE = "localization-string-tables-turkish_assets_all.bundle"
UI_BUNDLE_GLOB = "ui_assets_all_*.bundle"
CJK_FONT_ASSET = "NotoSansSC-Black SDF"
BACKUP_DIR = Path(__file__).resolve().parent.parent / ".spike-backup"

# "m_Crc":<数字>，UTF-16LE 编码，字节级匹配以免受奇偶对齐影响
CRC_PATTERN = re.compile(rb'"\x00m\x00_\x00C\x00r\x00c\x00"\x00:\x00((?:[0-9]\x00)+)')

# 主菜单与设置页的若干 Menus 条目（m_Id → 译文）
SAMPLE_MENUS = {
    248174071668736: "生涯",
    81154120728502272: "继续",
    86591412498653184: "快速比赛",
    86591482774216704: "设置",
    86591518455160832: "附加内容",
    86591545999155200: "退出",
    86592408041873408: "加入愿望单",
    90292244167581696: "设置",
    90295701435899904: "游戏",
    90295732415029248: "图形",
    90295768498626560: "音频",
    90295793224048640: "操作",
    90295828611391488: "界面",
    90295899608375296: "语言",
    91281112169766912: "显示",
    91281169468153856: "分辨率",
}


def default_bundle_dir() -> Path:
    return GAME_DIR / "Contents/Resources/Data/StreamingAssets/aa/StandaloneOSX"


def disable_bundle_crc(catalog_text: str) -> str:
    """把 catalog 中所有包的 m_Crc 改为 0，用空格补齐原长度，使二进制 blob 的长度前缀保持有效。"""
    catalog = json.loads(catalog_text)
    old_b64 = catalog["m_ExtraDataString"]

    def zero(m: re.Match) -> bytes:
        width = len(m.group(1)) // 2
        return m.group(0)[: -len(m.group(1))] + ("0" + " " * (width - 1)).encode("utf-16-le")

    new_b64 = base64.b64encode(CRC_PATTERN.sub(zero, base64.b64decode(old_b64))).decode()
    # 只替换 blob 本身，其余文本原样保留
    return catalog_text.replace(old_b64, new_b64)


def patch_string_table(bundle: bytes, translations: dict[int, str]) -> bytes:
    """按 m_Id 把字符串表中的 m_Localized 替换为译文。"""
    env = UnityPy.load(bundle)
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        tree = obj.read_typetree()
        hit = False
        for entry in tree["m_TableData"]:
            if entry["m_Id"] in translations:
                entry["m_Localized"] = translations[entry["m_Id"]]
                hit = True
        if hit:
            obj.save_typetree(tree)
    return env.file.save(packer="lz4")


def add_cjk_fallback(bundle: bytes) -> bytes:
    """把 NotoSansSC-Black SDF 追加到包内其余 TMP 字体的后备链末尾（已含则跳过）。"""
    env = UnityPy.load(bundle)
    fonts = []
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if "m_FaceInfo" in tree:
            fonts.append((obj, tree))

    cjk_id = next(obj.path_id for obj, tree in fonts if tree["m_Name"] == CJK_FONT_ASSET)
    for obj, tree in fonts:
        chain = tree["m_FallbackFontAssetTable"]
        if obj.path_id == cjk_id or any(r["m_FileID"] == 0 and r["m_PathID"] == cjk_id for r in chain):
            continue
        chain.append({"m_FileID": 0, "m_PathID": cjk_id})
        obj.save_typetree(tree)
    return env.file.save(packer="lz4")


def _targets() -> list[Path]:
    bundles = default_bundle_dir()
    return [bundles.parent / "catalog.json", bundles / TURKISH_BUNDLE, next(bundles.glob(UI_BUNDLE_GLOB))]


def apply() -> None:
    catalog, turkish, ui = _targets()
    BACKUP_DIR.mkdir(exist_ok=True)
    for path in (catalog, turkish, ui):
        if not (BACKUP_DIR / path.name).exists():
            shutil.copy2(path, BACKUP_DIR / path.name)
    # 每次都从备份重打，保证可重复运行
    catalog.write_text(disable_bundle_crc((BACKUP_DIR / catalog.name).read_text(encoding="utf-8")), encoding="utf-8")
    turkish.write_bytes(patch_string_table((BACKUP_DIR / turkish.name).read_bytes(), SAMPLE_MENUS))
    ui.write_bytes(add_cjk_fallback((BACKUP_DIR / ui.name).read_bytes()))
    print("已注入；进游戏把语言切到土耳其语查看")


def restore() -> None:
    for path in _targets():
        shutil.copy2(BACKUP_DIR / path.name, path)
    print("已还原")


if __name__ == "__main__":
    {"apply": apply, "restore": restore}[sys.argv[1]]()
