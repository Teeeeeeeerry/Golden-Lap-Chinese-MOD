"""命令行入口：python -m glzh <命令>"""

import sys
from pathlib import Path

from glzh import translations
from glzh.build import build
from glzh.game import DEFAULT_APP, GameFiles


def main(argv: list[str]) -> int:
    commands = {"validate": cmd_validate, "build": cmd_build}
    if len(argv) < 1 or argv[0] not in commands:
        print(f"用法：python -m glzh {{{'|'.join(commands)}}}")
        return 2
    return commands[argv[0]](argv[1:])


def cmd_validate(args: list[str]) -> int:
    errors = translations.validate_dir()
    for err in errors:
        print(err)
    print("译文校验通过" if not errors else f"共 {len(errors)} 处错误")
    return 1 if errors else 0


def cmd_build(args: list[str]) -> int:
    """python -m glzh build <输出目录>：从本地游戏文件构建，写到输出目录，不改动游戏。"""
    if len(args) != 1:
        print("用法：python -m glzh build <输出目录>")
        return 2
    out = Path(args[0])
    for rel, data in build(GameFiles.from_app(DEFAULT_APP)).items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_bytes(data)
        print(f"已写出 {out / rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
