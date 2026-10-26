"""命令行入口：python -m glzh <命令>"""

import sys

from glzh import translations


def main(argv: list[str]) -> int:
    commands = {"validate": cmd_validate}
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


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
