import hashlib
import os
import stat
import subprocess
import zipfile

import pytest

from scripts.release import REPO, RUNTIME, build_release, check_contents, check_runtime

ROOT = f"GoldenLap-zh-Hans-v{(REPO / 'VERSION').read_text().strip()}"
PY = f"{RUNTIME}/bin/python3.12"


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    """本机架构（arm64）的发布包；第一次构建要联网下载运行环境，之后用缓存。"""
    return build_release(tmp_path_factory.mktemp("dist"))


def names_in(archive) -> set[str]:
    with zipfile.ZipFile(archive) as zf:
        assert all(n.startswith(f"{ROOT}/") for n in zf.namelist())
        return {n.removeprefix(f"{ROOT}/") for n in zf.namelist()}


def test_release_contains_installer_restore_translations_readme_and_runtime(package):
    assert package.name == f"{ROOT}-macos-arm64.zip"
    names = names_in(package)
    assert {
        "install.command",
        "restore.command",
        "_env.sh",
        "README.md",
        "LICENSE",
        "requirements.txt",
        "src/glzh/__main__.py",
        "translations/LICENSE",
        "translations/zh-Hans/Content.json",
        "translations/zh-Hans/Menus.json",
        "translations/zh-Hans/Events.json",
        "runtime/THIRD-PARTY.md",
        PY,
        f"{RUNTIME}/lib/python3.12/LICENSE.txt",
        f"{RUNTIME}/LICENSE.python-build-standalone.txt",
        f"{RUNTIME}/lib/python3.12/site-packages/UnityPy/__init__.py",
        f"{RUNTIME}/lib/python3.12/site-packages/tpk_ar/__init__.py",
    } <= names
    # FMOD 是商业授权，不随包分发（ADR 0007）
    assert not [n for n in names if "fmod" in n.lower()]
    with zipfile.ZipFile(package) as zf:
        # 解压后脚本可直接双击，内置 Python 可直接运行
        for name in ("install.command", PY):
            assert zf.getinfo(f"{ROOT}/{name}").external_attr >> 16 & stat.S_IXUSR, name


def test_release_contains_no_game_resources(package):
    names = names_in(package)
    assert not [n for n in names if n.endswith((".bundle", ".asset", ".png", ".ttf", ".otf"))]
    project = [n for n in names if not n.startswith("runtime/")]
    assert not [n for n in project if n.endswith("catalog.json") or "__pycache__" in n]


def test_release_is_reproducible(package, tmp_path):
    again = build_release(tmp_path)
    assert hashlib.sha256(again.read_bytes()).digest() == hashlib.sha256(package.read_bytes()).digest()


@pytest.mark.parametrize("name", ["src/glzh/.DS_Store", "translations/x.bundle", "fonts/NotoSansSC.otf"])
def test_check_contents_rejects_non_project_files(name):
    with pytest.raises(ValueError, match=name):
        check_contents([name])


@pytest.mark.parametrize(
    "name", [f"{RUNTIME}/lib/python3.12/fonts/DejaVuSans.ttf", f"{RUNTIME}/lib/python3.12/catalog.json", f"{RUNTIME}/lib/tk9.0/tk.tcl", f"{RUNTIME}/share/x.1"]
)
def test_check_runtime_rejects_anything_outside_the_allowlist(name):
    with pytest.raises(ValueError, match=name):
        check_runtime([name])


def run(script, game, home):
    """像玩家一样运行包里的脚本：PATH 里没有 Python 3.11+，HOME 是空的临时目录。"""
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin", "GOLDEN_LAP_APP": str(game.app), "LANG": "zh_CN.UTF-8"}
    return subprocess.run(["/bin/bash", str(script)], env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600)


def shas(game, rels) -> dict[str, str]:
    return {rel: hashlib.sha256((game.data / rel).read_bytes()).hexdigest() for rel in rels}


def test_release_installs_and_restores_without_system_python(package, fake_game, originals, tmp_path):
    # 用 ditto 解压，与访达双击 zip 的效果一致（保留可执行位）
    subprocess.run(["ditto", "-x", "-k", str(package), str(tmp_path)], check=True)
    root, home = tmp_path / ROOT, tmp_path / "home"
    home.mkdir()

    result = run(root / "install.command", fake_game, home)
    assert result.returncode == 0, result.stdout + result.stderr
    after = shas(fake_game, originals)
    assert after != originals and after["resources.assets"] != originals["resources.assets"]
    # 没有走「找系统 Python、建虚拟环境、联网装依赖」的老路
    assert not (home / "Library/Application Support/GoldenLapZH/venv").exists()
    assert "正在准备运行环境" not in result.stdout

    result = run(root / "restore.command", fake_game, home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert shas(fake_game, originals) == originals
    assert os.access(root / PY, os.X_OK)
