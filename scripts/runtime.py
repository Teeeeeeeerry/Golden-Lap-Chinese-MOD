"""组装发布包内置的运行环境：独立 Python 加上预先装好的依赖（见 ADR 0007）。

版本、下载地址和 sha256 全部取自 packaging/runtime.lock.json（由 scripts/lock_runtime.py 生成）。
下载内容按 sha256 校验后缓存在仓库外，组装每次在新的临时目录里从头进行，同样的锁定文件得到同样的内容。
不用 pip 安装：wheel 就是 zip，按规范解压进 site-packages 即可，构建不依赖网络上的其他东西。
"""

import hashlib
import json
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCK = REPO / "packaging" / "runtime.lock.json"
CACHE = Path.home() / "Library" / "Caches" / "GoldenLapZH-build"
PYTHON = "python3.12"  # 入口；同目录下的其余启动器都是指向它的符号链接，删掉
SITE = f"lib/{PYTHON}/site-packages"
LICENSE = "LICENSE.python-build-standalone.txt"  # 解释器构建项目本身的许可证（MPL-2.0）；CPython 的在标准库目录里
# 运行环境里只应有这些：解释器、它链接的动态库、标准库与依赖、许可证
ALLOWED = (f"bin/{PYTHON}", "lib/libpython3.12.dylib", f"lib/{PYTHON}/", LICENSE)

# 运行汉化用不到的部分（glob 模式）：图形界面（tkinter、IDLE 及 Tcl/Tk）、pip、头文件、手册、测试
PRUNE = [
    "include",
    "share",
    "lib/pkgconfig",
    "lib/tcl*",
    "lib/tk*",
    "lib/itcl*",
    "lib/thread*",
    "lib/libtcl*",
    "lib/libtk*",
    f"lib/{PYTHON}/config-3.12-darwin",
    f"lib/{PYTHON}/ensurepip",
    f"lib/{PYTHON}/idlelib",
    f"lib/{PYTHON}/test",
    f"lib/{PYTHON}/tkinter",
    f"lib/{PYTHON}/turtledemo",
    f"lib/{PYTHON}/lib-dynload/_tkinter.cpython-312-darwin.so",
]


def lock() -> dict:
    return json.loads(LOCK.read_text())


def fetch(url: str, sha256: str, cache: Path = CACHE) -> Path:
    """下载到缓存并校验 sha256；缓存里已有且校验通过的不再下载。"""
    path = cache / "downloads" / url.rsplit("/", 1)[1]
    if not (path.exists() and _sha256(path) == sha256):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, "wb") as out:
            shutil.copyfileobj(resp, out)
        if _sha256(tmp) != sha256:
            tmp.unlink()
            raise ValueError(f"{path.name} 的 sha256 与锁定文件不符，可能下载出错或被篡改")
        tmp.replace(path)
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _install_wheel(wheel: Path, site: Path) -> None:
    """按 wheel 规范解压：<名>.data/ 下的 purelib、platlib 并入 site-packages，脚本、头文件、手册等用不到，跳过。"""
    with zipfile.ZipFile(wheel) as zf:
        for info in zf.infolist():
            top, _, rest = info.filename.partition("/")
            if top.endswith(".data"):
                scheme, _, rest = rest.partition("/")
                if scheme not in ("purelib", "platlib") or not rest:
                    continue
                info.filename = rest
            zf.extract(info, site)


def _install_sdist(sdist: Path, name: str, site: Path) -> None:
    """纯 Python 源码包：取出包目录，并写一份最简 dist-info 和许可证。"""
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(sdist) as tf:
            tf.extractall(tmp, filter="data")
        (root,) = Path(tmp).iterdir()
        shutil.copytree(root / name, site / name)
        version = root.name.rsplit("-", 1)[1]
        info = site / f"{name}-{version}.dist-info"
        info.mkdir()
        (info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")
        shutil.copy2(root / "LICENSE", info / "LICENSE")


def build_runtime(arch: str, dest: Path, cache: Path = CACHE) -> Path:
    """在 dest 下组装 arch 架构的运行环境，返回其根目录（dest/python）。"""
    spec = lock()
    with tarfile.open(fetch(**spec["python"][arch], cache=cache)) as tf:
        tf.extractall(dest, filter="data")
    root = dest / "python"
    for pattern in PRUNE:
        for path in root.glob(pattern):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
    for path in (root / "bin").iterdir():
        if path.name != PYTHON:
            path.unlink()
    site = root / SITE
    for path in site.iterdir():
        if path.name.startswith("pip"):
            shutil.rmtree(path)
    for wheel in spec["wheels"][arch]:
        _install_wheel(fetch(wheel["url"], wheel["sha256"], cache), site)
    shutil.copy2(fetch(**spec["python"]["license"], cache=cache), root / LICENSE)
    for sdist in spec["sdists"]:
        _install_sdist(fetch(sdist["url"], sdist["sha256"], cache), sdist["name"], site)
    links = [p for p in root.rglob("*") if p.is_symlink()]
    if links:
        raise ValueError(f"运行环境里还有符号链接，zip 解压后会失效：{links[:3]}")
    return root
