import stat
import zipfile

from scripts.release import build_release


def test_release_contains_installer_restore_translations_and_readme(tmp_path):
    archive = build_release(tmp_path)
    version = open("VERSION").read().strip()
    root = f"GoldenLap-zh-Hans-v{version}"
    assert archive.name == f"{root}.zip"
    with zipfile.ZipFile(archive) as zf:
        names = {n.removeprefix(f"{root}/") for n in zf.namelist()}
        assert all(n.startswith(f"{root}/") for n in zf.namelist())
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
        } <= names
        # 解压后脚本可直接双击
        mode = zf.getinfo(f"{root}/install.command").external_attr >> 16
        assert mode & stat.S_IXUSR


def test_release_contains_no_game_resources(tmp_path):
    with zipfile.ZipFile(build_release(tmp_path)) as zf:
        names = zf.namelist()
    assert not [n for n in names if n.endswith((".bundle", ".asset", ".png", ".ttf", ".otf"))]
    assert not [n for n in names if n.endswith("catalog.json") or "__pycache__" in n]
