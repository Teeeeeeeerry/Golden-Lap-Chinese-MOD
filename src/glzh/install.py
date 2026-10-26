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
from glzh.game import GameFiles

BACKUP_DIR = Path.home() / "Library/Application Support/GoldenLapZH/backup"
MANIFEST = "patched.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inputs(game: GameFiles) -> list[Path]:
    """构建需要读取的原始文件（相对 aa 目录）。"""
    return [p.relative_to(game.aa) for p in (game.catalog, game.english, game.turkish, game.locales, game.ui)]


def _write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".glzh-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def install(game: GameFiles, backup_dir: Path = BACKUP_DIR, translations_dir: Path = translations.DEFAULT_DIR) -> list[str]:
    """备份并注入，返回写入游戏的文件（相对 aa 目录）。"""
    backup = GameFiles(backup_dir)
    manifest_path = backup_dir / MANIFEST
    patched = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for rel in _inputs(game):
        current = game.aa / rel
        if patched.get(rel.as_posix()) != _sha256(current) or not (backup_dir / rel).exists():
            (backup_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(current, backup_dir / rel)
    # 游戏更新后 ui 包换了哈希文件名，清掉旧的备份，免得 glob 匹配到两个
    for stale in backup.bundles.glob("ui_assets_all_*.bundle"):
        if stale.name != game.ui.name:
            stale.unlink()

    outputs = build(backup, translations_dir)
    for rel, data in outputs.items():
        _write_atomic(game.aa / rel, data)
    manifest_path.write_text(json.dumps({rel: hashlib.sha256(data).hexdigest() for rel, data in outputs.items()}, indent=2))
    return sorted(outputs)


def restore(game: GameFiles, backup_dir: Path = BACKUP_DIR) -> list[str]:
    """把被改动的文件从备份拷回游戏，返回还原的文件；备份不完整时不做任何改动并报错。"""
    manifest_path = backup_dir / MANIFEST
    if not manifest_path.exists():
        raise FileNotFoundError(f"没有找到安装记录 {manifest_path}，可能从未安装过汉化，游戏未做改动")
    targets = list(json.loads(manifest_path.read_text()))
    missing = [rel for rel in targets if not (backup_dir / rel).exists()]
    if missing:
        raise FileNotFoundError(f"备份缺少 {', '.join(missing)}，为免损坏游戏未做改动；可在 Steam 中“验证游戏文件完整性”恢复原版")
    for rel in targets:
        _write_atomic(game.aa / rel, (backup_dir / rel).read_bytes())
    manifest_path.unlink()
    return targets
