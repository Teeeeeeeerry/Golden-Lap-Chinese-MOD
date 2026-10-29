"""生成发布包：把安装器、还原脚本、译文、玩家说明和内置运行环境打成 GitHub Release 用的 zip。

发布包不含任何游戏原始资源，也不含字体（ADR 0002、0003）：中文字形复用玩家本地游戏自带的思源黑体。
项目文件只收录 git 跟踪的，本地导出的调试文件、.DS_Store 等不会混入。
内置运行环境（独立 Python 加依赖）按锁定文件组装，玩家不用自己装 Python，安装时也不联网（ADR 0007）。
"""

import os
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from glzh import translations  # noqa: E402
from scripts.runtime import ALLOWED, CACHE, build_runtime  # noqa: E402

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
    ("packaging/THIRD-PARTY.md", "runtime/THIRD-PARTY.md"),
]
ARCHS = ("arm64", "x86_64")  # Apple 芯片、Intel；运行环境分架构，每种芯片一个发布包
RUNTIME = "runtime/python"
# 白名单之内也拦住游戏资源和字体
RUNTIME_FORBIDDEN = (".bundle", ".asset", ".resS", ".ttf", ".otf", ".ttc", "catalog.json")
ALLOWED_SUFFIXES = {".command", ".sh", ".py", ".json", ".txt", ".md", ""}


def _tracked(repo: Path, path: str) -> list[tuple[str, int]]:
    """git 跟踪的文件及其在索引里的权限位；按索引取，不受本地 chmod 影响，构建可复现。"""
    out = subprocess.run(["git", "ls-files", "-s", "--", path], cwd=repo, capture_output=True, text=True, check=True)
    return [(line.split("\t", 1)[1], 0o755 if line.startswith("100755") else 0o644) for line in out.stdout.splitlines()]


def release_files(repo: Path = REPO) -> list[tuple[Path, str, int]]:
    """待收录的 (源文件, 包内路径, 权限位)，按包内路径排序。"""
    files = []
    for src, dst in LAYOUT:
        tracked = _tracked(repo, src)
        if not tracked:
            raise FileNotFoundError(f"{src} 未被 git 跟踪，不能收录进发布包")
        for rel, mode in tracked:
            files.append((repo / rel, dst + rel[len(src) :], mode))
    return sorted(files, key=lambda item: item[1])


def check_contents(names: list[str]) -> None:
    """发布包的项目文件只允许脚本、源码、译文与文档。"""
    for name in names:
        if Path(name).suffix not in ALLOWED_SUFFIXES or Path(name).name.startswith("."):
            raise ValueError(f"发布包不应包含 {name}：只允许脚本、源码、译文与文档")


def check_runtime(names: list[str]) -> None:
    """运行环境只允许解释器、标准库、依赖与许可证，且不应混入游戏资源或字体。"""
    for name in names:
        rel = name.removeprefix(f"{RUNTIME}/")
        if not rel.startswith(ALLOWED) or name.endswith(RUNTIME_FORBIDDEN):
            raise ValueError(f"运行环境不应包含 {name}")


def runtime_files(arch: str, dest: Path, cache: Path = CACHE) -> list[tuple[Path, str, int]]:
    """在 dest 下组装运行环境，返回 (源文件, 包内路径, 权限位)，按包内路径排序；可执行位取自上游文件。"""
    root = build_runtime(arch, dest, cache)
    files = [(p, f"{RUNTIME}/{p.relative_to(root).as_posix()}", 0o755 if os.stat(p).st_mode & 0o111 else 0o644) for p in root.rglob("*") if p.is_file()]
    return sorted(files, key=lambda item: item[1])


def build_release(out_dir: Path, repo: Path = REPO, arch: str = "arm64", cache: Path = CACHE) -> Path:
    """在 out_dir 生成 GoldenLap-zh-Hans-v<版本>-macos-<架构>.zip，返回其路径；译文校验不通过时报错。"""
    errors = translations.validate_dir(repo / "translations" / "zh-Hans")
    if errors:
        raise ValueError("译文校验不通过：\n" + "\n".join(errors))
    files = release_files(repo)
    check_contents([name for _, name, _ in files])
    root = f"{PREFIX}-v{(repo / 'VERSION').read_text().strip()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"{root}-macos-{arch}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        runtime = runtime_files(arch, Path(tmp), cache)
        check_runtime([name for _, name, _ in runtime])
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for src, name, mode in files + runtime:
                info = zipfile.ZipInfo(f"{root}/{name}", date_time=(2026, 1, 1, 0, 0, 0))
                info.external_attr = (stat.S_IFREG | mode) << 16  # 保留可执行位，解压后脚本可直接双击、Python 可直接运行
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, src.read_bytes())
    return archive


def build_releases(out_dir: Path, repo: Path = REPO, cache: Path = CACHE) -> dict[str, Path]:
    """为每种芯片各生成一个发布包：架构 → zip 路径。"""
    return {arch: build_release(out_dir, repo, arch, cache) for arch in ARCHS}


def main(argv: list[str]) -> int:
    for archive in build_releases(Path(argv[0]) if argv else REPO / "dist").values():
        print(archive)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
