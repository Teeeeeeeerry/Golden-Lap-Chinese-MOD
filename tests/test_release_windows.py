import hashlib
import os
import subprocess
import sys
import zipfile

import pytest

from scripts.release import ARCHS, REPO, RUNTIME, WINDOWS, build_release, check_runtime, check_tag, release_files

ROOT = f"GoldenLap-zh-Hans-v{(REPO / 'VERSION').read_text(encoding='utf-8').strip()}"
PY = f"{RUNTIME}/python.exe"


def packaged(arch: str) -> set[str]:
    return {name for _, name, _ in release_files(arch=arch)}


def test_each_package_carries_only_its_own_platform():
    windows = packaged(WINDOWS)
    assert {"install.bat", "restore.bat", "_run.bat", "src/glzh_windows/__main__.py", "src/glzh/cli.py", "README.md"} <= windows
    assert not [name for name in windows if "macos" in name or name.endswith((".command", ".sh"))]
    for arch in ARCHS:
        assert not [name for name in packaged(arch) if "windows" in name or name.endswith(".bat")]


def test_windows_player_readme_is_the_windows_one():
    source = {name: src for src, name, _ in release_files(arch=WINDOWS)}["README.md"]
    assert "install.bat" in source.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "name", [f"{RUNTIME}/Scripts/pip.exe", f"{RUNTIME}/tcl/tk8.6/tk.tcl", f"{RUNTIME}/Lib/fonts/DejaVuSans.ttf", f"{RUNTIME}/pythonw.exe"]
)
def test_windows_runtime_allowlist_rejects_everything_else(name):
    with pytest.raises(ValueError, match=name):
        check_runtime([name], WINDOWS)


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    """Windows 发布包；第一次构建要联网下载运行环境，之后用缓存。"""
    if sys.platform != "win32":
        pytest.skip("Windows 发布包只在 Windows 上构建和运行")
    return build_release(tmp_path_factory.mktemp("dist"), arch=WINDOWS)


def names_in(archive) -> set[str]:
    with zipfile.ZipFile(archive) as zf:
        assert all(n.startswith(f"{ROOT}/") for n in zf.namelist())
        return {n.removeprefix(f"{ROOT}/") for n in zf.namelist()}


def test_package_name_and_contents(package):
    assert package.name == f"{ROOT}-windows-x86_64.zip"
    names = names_in(package)
    assert {
        "install.bat",
        "runtime/THIRD-PARTY.md",
        PY,
        f"{RUNTIME}/python312.dll",
        f"{RUNTIME}/LICENSE.txt",
        f"{RUNTIME}/LICENSE.python-build-standalone.txt",
        f"{RUNTIME}/Lib/site-packages/UnityPy/__init__.py",
        f"{RUNTIME}/Lib/site-packages/tpk_ar/__init__.py",
    } <= names
    # FMOD 是商业授权，不随包分发（ADR 0007）
    assert not [n for n in names if "fmod" in n.lower()]


def test_package_contains_no_game_resources(package):
    names = names_in(package)
    assert not [n for n in names if n.endswith((".bundle", ".asset", ".png", ".ttf", ".otf"))]
    project = [n for n in names if not n.startswith("runtime/")]
    assert not [n for n in project if n.endswith("catalog.json") or "__pycache__" in n]


def test_package_is_reproducible(package, tmp_path):
    again = build_release(tmp_path, arch=WINDOWS)
    assert hashlib.sha256(again.read_bytes()).digest() == hashlib.sha256(package.read_bytes()).digest()


def run(script, game, home):
    """像玩家一样双击：PATH 里没有 Python，备份目录是空的临时目录。"""
    env = {
        "SystemRoot": os.environ["SystemRoot"],
        "PATH": rf"{os.environ['SystemRoot']}\System32",
        "GOLDEN_LAP_DIR": str(game.data.parent),
        "LOCALAPPDATA": str(home),
    }
    return subprocess.run(["cmd", "/c", str(script)], env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=600)


def shas(game, rels) -> dict[str, str]:
    return {rel: hashlib.sha256((game.data / rel).read_bytes()).hexdigest() for rel in rels}


def test_package_installs_and_restores_without_system_python(package, fake_game, originals, tmp_path):
    target = tmp_path / "下载 目录"  # 路径含空格和中文
    with zipfile.ZipFile(package) as zf:
        zf.extractall(target)
    root, home = target / ROOT, tmp_path / "home"
    home.mkdir()

    result = run(root / "install.bat", fake_game, home)
    output = result.stdout.decode("utf-8", "replace")
    assert result.returncode == 0, output + result.stderr.decode("utf-8", "replace")
    assert "完成" in output
    after = shas(fake_game, originals)
    assert after["resources.assets"] != originals["resources.assets"] and after["level2"] != originals["level2"]
    assert (home / "GoldenLapZH/backup/patched.json").exists()

    result = run(root / "restore.bat", fake_game, home)
    assert result.returncode == 0, result.stdout.decode("utf-8", "replace")
    assert shas(fake_game, originals) == originals


def test_tag_must_match_version():
    version = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    assert check_tag(f"v{version}")
    assert not check_tag(f"v{version}9") and not check_tag(version)
