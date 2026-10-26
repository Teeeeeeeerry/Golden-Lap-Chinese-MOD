"""生成发布包：把安装器、还原脚本、译文与玩家说明打成 GitHub Release 用的 zip。

发布包只含自有资源（ADR 0002）：脚本、Python 源码、译文与文档，不含任何游戏原始资源，
也不含字体——中文字形复用玩家本地游戏自带的思源黑体（ADR 0003）。
只收录 git 跟踪的文件，本地导出的调试文件、.DS_Store 等不会混入。
"""

import stat
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from glzh import translations  # noqa: E402

PREFIX = "GoldenLap-zh-Hans"

# (仓库内路径, 包内路径)；目录按其下 git 跟踪的文件逐个加入
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


def _tracked(repo: Path, path: str) -> list[str]:
    out = subprocess.run(["git", "ls-files", "--", path], cwd=repo, capture_output=True, text=True, check=True)
    return out.stdout.splitlines()


def release_files(repo: Path = REPO) -> list[tuple[Path, str]]:
    """待收录的 (源文件, 包内路径)，按包内路径排序。"""
    files = []
    for src, dst in LAYOUT:
        tracked = _tracked(repo, src)
        if not tracked:
            raise FileNotFoundError(f"{src} 未被 git 跟踪，不能收录进发布包")
        for rel in tracked:
            files.append((repo / rel, dst + rel[len(src) :]))
    return sorted(files, key=lambda item: item[1])


def check_contents(files: list[tuple[Path, str]]) -> None:
    """发布包只允许脚本、源码、译文与文档。"""
    for _, name in files:
        if Path(name).suffix not in ALLOWED_SUFFIXES or Path(name).name.startswith("."):
            raise ValueError(f"发布包不应包含 {name}：只允许脚本、源码、译文与文档")


def build_release(out_dir: Path, repo: Path = REPO) -> Path:
    """在 out_dir 生成 GoldenLap-zh-Hans-v<版本>.zip，返回其路径；译文校验不通过时报错。"""
    errors = translations.validate_dir(repo / "translations" / "zh-Hans")
    if errors:
        raise ValueError("译文校验不通过：\n" + "\n".join(errors))
    files = release_files(repo)
    check_contents(files)
    root = f"{PREFIX}-v{(repo / 'VERSION').read_text().strip()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"{root}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for src, name in files:
            info = zipfile.ZipInfo(f"{root}/{name}", date_time=(2026, 1, 1, 0, 0, 0))
            mode = 0o755 if name.endswith(".command") else 0o644  # 保留可执行位，解压后可直接双击
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, src.read_bytes())
    return archive


def main(argv: list[str]) -> int:
    print(build_release(Path(argv[0]) if argv else REPO / "dist"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
