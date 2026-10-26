"""发布打包：把安装器、还原脚本、译文与说明打成 GitHub Release 用的 zip。

发布包只含自有资源（ADR 0002）：脚本、Python 源码、译文与文档，不含任何游戏原始资源，
也不含字体——中文字形复用玩家本地游戏自带的思源黑体（ADR 0003）。
"""

import stat
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PREFIX = "GoldenLap-zh-Hans"

# (仓库内路径, 包内路径)；目录按其下的文件逐个加入
LAYOUT = [
    ("macos/install.command", "install.command"),
    ("macos/restore.command", "restore.command"),
    ("macos/_env.sh", "_env.sh"),
    ("src/glzh", "src/glzh"),
    ("translations", "translations"),
    ("requirements.txt", "requirements.txt"),
    ("docs/release-README.md", "README.md"),
    ("LICENSE", "LICENSE"),
    ("VERSION", "VERSION"),
]
ALLOWED_SUFFIXES = {".command", ".sh", ".py", ".json", ".txt", ".md", ""}


def release_files(repo: Path = REPO) -> list[tuple[Path, str]]:
    """待打包的 (源文件, 包内路径)，按包内路径排序。"""
    files = []
    for src, dst in LAYOUT:
        path = repo / src
        if path.is_dir():
            for f in sorted(path.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts:
                    files.append((f, f"{dst}/{f.relative_to(path).as_posix()}"))
        else:
            files.append((path, dst))
    for f, name in files:
        if f.suffix not in ALLOWED_SUFFIXES:
            raise ValueError(f"发布包不应包含 {name}：只允许脚本、源码、译文与文档")
    return sorted(files, key=lambda item: item[1])


def build_release(out_dir: Path, repo: Path = REPO) -> Path:
    version = (repo / "VERSION").read_text().strip()
    root = f"{PREFIX}-v{version}"
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"{root}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for src, name in release_files(repo):
            info = zipfile.ZipInfo(f"{root}/{name}", date_time=(2026, 1, 1, 0, 0, 0))
            mode = 0o755 if name.endswith(".command") else 0o644  # 保留可执行位，解压后可直接双击
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, src.read_bytes())
    return archive


if __name__ == "__main__":
    print(build_release(Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "dist"))
