from pathlib import Path

from glzh import install
from glzh.cli import main
from glzh.game import GameFiles


class FakePlatform:
    locate_hint = "按这里的提示操作。"

    def __init__(self, data: Path, problem: str | None = None):
        self.files, self.problem, self.backup_dir = GameFiles(data, "StandaloneTest"), problem, data / "backup"

    def game(self) -> GameFiles:
        return self.files

    def preflight(self) -> str | None:
        return self.problem


def test_unknown_command_prints_usage(tmp_path, capsys):
    assert main(["nope"], FakePlatform(tmp_path)) == 2
    assert "install" in capsys.readouterr().out


def test_install_explains_how_to_locate_the_game(tmp_path, capsys):
    assert main(["install"], FakePlatform(tmp_path)) == 1
    assert "按这里的提示操作。" in capsys.readouterr().out


def test_restore_explains_how_to_locate_the_game(tmp_path, capsys):
    assert main(["restore"], FakePlatform(tmp_path)) == 1
    assert "按这里的提示操作。" in capsys.readouterr().out


def test_restore_stops_before_touching_anything_when_preflight_fails(tmp_path, capsys, monkeypatch):
    platform = FakePlatform(tmp_path, "请先退出游戏。")
    platform.files.catalog.parent.mkdir(parents=True)
    platform.files.catalog.write_text("{}")
    monkeypatch.setattr(install, "restore", lambda *_: fail_if_called())
    assert main(["restore"], platform) == 1
    assert "请先退出游戏。" in capsys.readouterr().out


def test_install_stops_before_touching_anything_when_preflight_fails(tmp_path, capsys, monkeypatch):
    platform = FakePlatform(tmp_path, "请先退出游戏。")
    monkeypatch.setattr(GameFiles, "exists", lambda self: True)
    monkeypatch.setattr(install, "install", lambda *_: fail_if_called())
    assert main(["install"], platform) == 1
    assert "请先退出游戏。" in capsys.readouterr().out


def fail_if_called():
    raise AssertionError("运行前检查未通过时不应改动游戏")
