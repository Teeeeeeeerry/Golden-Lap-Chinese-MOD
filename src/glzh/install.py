"""安装：备份玩家本地的原始文件，从备份构建并写回游戏。

备份目录布局与游戏的 Addressables 目录（StreamingAssets/aa）一致，便于直接作为构建输入：

    <备份目录>/catalog.json
    <备份目录>/StandaloneOSX/<被改动的包与英文字符串表包>
    <备份目录>/patched.json   上次写入游戏的各文件 sha256

每次安装都从备份重新构建，因此可重复运行且结果一致。当前游戏文件与 patched.json 不符，
说明游戏已更新或被"验证文件完整性"还原，此时先用当前文件刷新备份。
"""

import hashlib
import json
import os
import shutil
from pathlib import Path

from glzh import translations
from glzh.build import build
from glzh.catalog import bundle_crcs
from glzh.game import UI_BUNDLE_GLOB, GameFiles

BACKUP_DIR = Path.home() / "Library/Application Support/GoldenLapZH/backup"
MANIFEST = "patched.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AlreadyPatched(RuntimeError):
    """游戏文件已被改过，却没有对应的安装记录，无法取得原版备份。"""


def _write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".glzh-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def install(game: GameFiles, backup_dir: Path = BACKUP_DIR, translations_dir: Path = translations.DEFAULT_DIR) -> list[str]:
    """备份并注入，返回写入游戏的文件（相对 aa 目录）。"""
    backup = GameFiles(backup_dir)
    manifest_path = backup_dir / MANIFEST
    patched = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    to_backup = []
    for path in game.inputs:
        rel, digest = path.relative_to(game.aa).as_posix(), _sha256(path)
        if patched.get(rel) == digest:
            continue  # 是上次写入的产物，备份里已是原版
        if (backup_dir / rel).exists() and _sha256(backup_dir / rel) == digest:
            continue  # 未被改动的原版（如英文包），已备份
        to_backup.append(path)
    # 备份前确认当前文件是原版：catalog 中土耳其语包 CRC 为 0 说明游戏已被改过（例如删掉了备份目录后重跑）
    if to_backup and bundle_crcs(game.catalog.read_text(encoding="utf-8")).get(game.turkish.name) == 0:
        raise AlreadyPatched(
            "游戏文件已被修改过，但找不到对应的原版备份。请先在 Steam 中右键 Golden Lap → 属性 → 已安装文件 → "
            "验证游戏文件的完整性，恢复原版后再运行安装器。"
        )
    for path in to_backup:
        dst = backup_dir / path.relative_to(game.aa)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
    # 游戏更新后 ui 包换了哈希文件名，清掉旧的备份，免得 glob 匹配到两个
    for stale in backup.bundles.glob(UI_BUNDLE_GLOB):
        if stale.name != game.ui.name:
            stale.unlink()

    outputs = build(backup, translations_dir)
    # 先记下将要写入的哈希再写游戏：中途中断时，已写入的文件与记录一致，不会被误当作原版备份
    patched = {rel: hashlib.sha256(data).hexdigest() for rel, data in outputs.items()}
    manifest_path.write_text(json.dumps(patched, indent=2))
    for rel, data in outputs.items():
        _write_atomic(game.aa / rel, data)
    return sorted(outputs)

