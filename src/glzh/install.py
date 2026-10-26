"""安装与还原：备份玩家本地的原始文件，从备份构建并写回游戏；还原时把备份拷回。

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


VERIFY_HINT = "可在 Steam 中右键 Golden Lap → 属性 → 已安装文件 → 验证游戏文件的完整性，恢复原版。"


class AlreadyPatched(RuntimeError):
    """游戏文件已被改过，却没有对应的安装记录，无法取得原版备份。"""


class NotInstalled(RuntimeError):
    """没有安装记录，无从还原。"""


class BackupIncomplete(RuntimeError):
    """需要还原的文件缺少备份。"""


def _read_manifest(backup_dir: Path) -> dict[str, str]:
    path = backup_dir / MANIFEST
    return json.loads(path.read_text()) if path.exists() else {}


def _write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".glzh-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def install(game: GameFiles, backup_dir: Path = BACKUP_DIR, translations_dir: Path = translations.DEFAULT_DIR) -> list[str]:
    """备份并注入，返回写入游戏的文件（相对 aa 目录）。"""
    backup = GameFiles(backup_dir)
    manifest_path = backup_dir / MANIFEST
    patched = _read_manifest(backup_dir)
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
        raise AlreadyPatched(f"游戏文件已被修改过，但找不到对应的原版备份。{VERIFY_HINT}恢复后再运行安装器。")
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


def restore(game: GameFiles, backup_dir: Path = BACKUP_DIR) -> tuple[list[str], list[str]]:
    """把安装器写入的文件从备份拷回游戏，返回 (已还原, 已跳过) 的文件（相对 aa 目录）。

    只还原内容仍等于安装记录的文件：已被游戏更新或"验证文件完整性"覆盖的文件本就是原版，
    用旧备份回退反而会与新版游戏不一致，跳过。找不到游戏或备份不完整时不做任何改动并报错。
    """
    if not game.catalog.exists():
        raise FileNotFoundError(f"没有在 {game.aa} 找到 Golden Lap，未做任何改动")
    patched = _read_manifest(backup_dir)
    if not patched:
        raise NotInstalled(f"没有找到安装记录（{backup_dir / MANIFEST}），未做任何改动。若游戏仍显示汉化，{VERIFY_HINT}")
    targets = sorted(rel for rel, digest in patched.items() if (game.aa / rel).exists() and _sha256(game.aa / rel) == digest)
    missing = [rel for rel in targets if not (backup_dir / rel).exists()]
    if missing:
        raise BackupIncomplete(f"备份缺少 {', '.join(missing)}，为免损坏游戏未做任何改动。{VERIFY_HINT}")
    for rel in targets:
        _write_atomic(game.aa / rel, (backup_dir / rel).read_bytes())
    (backup_dir / MANIFEST).unlink()
    return targets, sorted(patched.keys() - set(targets))
