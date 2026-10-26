"""命令行入口：python -m glzh <命令>"""

import sys
from pathlib import Path

from glzh import diff, markup, string_tables, translations
from glzh.build import build
from glzh.game import GameFiles, app_path

REPO = Path(__file__).resolve().parents[2]


def main(argv: list[str]) -> int:
    commands = {"validate": cmd_validate, "build": cmd_build, "diff": cmd_diff}
    if len(argv) < 1 or argv[0] not in commands:
        print(f"用法：python -m glzh {{{'|'.join(commands)}}}")
        return 2
    return commands[argv[0]](argv[1:])


def cmd_validate(args: list[str]) -> int:
    """校验译文格式；本机装有游戏时，再核对占位符、标签等标记与英文原文一致。"""
    errors = translations.validate_dir()
    src = GameFiles.from_app(app_path())
    if not errors and src.exists():
        errors = markup.markup_errors_dir(string_tables.read_tables(src.english.read_bytes()))
    for err in errors:
        print(err)
    print("译文校验通过" if not errors else f"共 {len(errors)} 处错误")
    return 1 if errors else 0


def cmd_build(args: list[str]) -> int:
    """python -m glzh build <输出目录>：从本地游戏文件构建，写到输出目录，不改动游戏。"""
    if len(args) != 1:
        print("用法：python -m glzh build <输出目录>")
        return 2
    out = Path(args[0]).resolve()
    if out.is_relative_to(REPO):
        print("输出目录不能在仓库内：产物含游戏原始资源，不得提交（见 ADR 0002）")
        return 2
    src = GameFiles.from_app(app_path())
    # 只报告不写回：构建在玩家本地运行，不改仓库译文
    diff_with_game(src)
    for rel, data in build(src).items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_bytes(data)
        print(f"已写出 {out / rel}")
    return 0


def diff_with_game(src: GameFiles) -> dict[str, diff.TableDiff]:
    """比对本地英文原文与仓库译文，并打印报告。"""
    english = string_tables.read_tables(src.english.read_bytes())
    diffs = diff.diff_against_english(english, translations.DEFAULT_DIR)
    print(diff.format_report(diffs))
    return diffs


def cmd_diff(args: list[str]) -> int:
    """python -m glzh diff [--write]：游戏更新后列出待译、待复核、废弃的条目；--write 把改动条目置 stale 写回。"""
    if args not in ([], ["--write"]):
        print("用法：python -m glzh diff [--write]")
        return 2
    # 只做格式校验：标记核对以当前英文为准，原文改动的条目正是这里要找出来的
    errors = translations.validate_dir()
    if errors:
        print("\n".join(errors))
        return 1
    diffs = diff_with_game(GameFiles.from_app(app_path()))
    if args == ["--write"]:
        for table, d in diffs.items():
            translations.save_table(translations.DEFAULT_DIR, table, d.updated)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
