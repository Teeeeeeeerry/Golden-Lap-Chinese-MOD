"""重新生成内置运行环境的锁定文件 packaging/runtime.lock.json（维护者在升级依赖时手动运行，需联网）。

依赖取自 requirements.txt，但去掉 fmod_toolkit：它内含商业授权的 FMOD 引擎，不随发布包分发，
UnityPy 只在导出音频时才加载它，汉化用不到（见 ADR 0007）。
每个依赖按目标架构让 pip 选出合适的 wheel，再从 PyPI 取下载地址和 sha256；
没有 wheel 的纯 Python 依赖记录源码包，构建时直接取出其中的包目录。
"""

import hashlib
import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from runtime import LOCK, REPO  # 与本脚本同在 scripts/ 下

PYTHON_RELEASE = "20261009"
PYTHON_VERSION = "3.12.15"
# 架构 → (python-build-standalone 的平台名, wheel 平台标签)
ARCHS = {"arm64": ("aarch64-apple-darwin", "macosx_11_0_arm64"), "x86_64": ("x86_64-apple-darwin", "macosx_11_0_x86_64")}
EXCLUDED = {"fmod_toolkit"}
SDIST_ONLY = {"tpk_ar"}  # 纯 Python，PyPI 上只有源码包


def requirements() -> list[str]:
    lines = (REPO / "requirements.txt").read_text().splitlines()
    reqs = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    return [r for r in reqs if r.split("==")[0] not in EXCLUDED]


def pypi_files(name: str, version: str) -> dict[str, dict]:
    with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=60) as resp:
        return {f["filename"]: {"url": f["url"], "sha256": f["digests"]["sha256"]} for f in json.load(resp)["urls"]}


def python_asset(arch: str) -> dict:
    name = f"cpython-{PYTHON_VERSION}+{PYTHON_RELEASE}-{ARCHS[arch][0]}-install_only.tar.gz"
    out = subprocess.run(
        ["gh", "api", f"repos/astral-sh/python-build-standalone/releases/tags/{PYTHON_RELEASE}", "-q", f'.assets[] | select(.name=="{name}") | .digest'],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if not out.startswith("sha256:"):
        raise ValueError(f"python-build-standalone {PYTHON_RELEASE} 里找不到 {name} 的 sha256")
    url = f"https://github.com/astral-sh/python-build-standalone/releases/download/{PYTHON_RELEASE}/{name}"
    return {"url": url, "sha256": out.removeprefix("sha256:")}


def wheel_for(req: str, platform: str) -> str:
    """让 pip 按目标平台选出 wheel，返回文件名（只下载这一个文件）。"""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [sys.executable, "-m", "pip", "download", "-q", "--no-deps", "--only-binary=:all:", "--platform", platform,
             "--python-version", PYTHON_VERSION.rsplit(".", 1)[0], "--implementation", "cp", req, "-d", tmp],
            check=True,
        )
        (wheel,) = Path(tmp).iterdir()
        return wheel.name


def lock() -> dict:
    result = {"python": {"version": PYTHON_VERSION, "release": PYTHON_RELEASE}, "sdists": [], "wheels": {arch: [] for arch in ARCHS}}
    for arch in ARCHS:
        result["python"][arch] = python_asset(arch)
    license_url = f"https://raw.githubusercontent.com/astral-sh/python-build-standalone/{PYTHON_RELEASE}/LICENSE"
    with urllib.request.urlopen(license_url, timeout=60) as resp:
        result["python"]["license"] = {"url": license_url, "sha256": hashlib.sha256(resp.read()).hexdigest()}
    for req in requirements():
        name, version = req.split("==")
        files = pypi_files(name, version)
        if name in SDIST_ONLY:
            (sdist,) = [f for f in files if f.endswith(".tar.gz")]
            result["sdists"].append({"name": name, "file": sdist, **files[sdist]})
            continue
        for arch, (_, platform) in ARCHS.items():
            wheel = wheel_for(req, platform)
            result["wheels"][arch].append({"file": wheel, **files[wheel]})
    return result


if __name__ == "__main__":
    LOCK.parent.mkdir(exist_ok=True)
    LOCK.write_text(json.dumps(lock(), indent=2, ensure_ascii=False) + "\n")
    print(f"已写出 {LOCK}")
