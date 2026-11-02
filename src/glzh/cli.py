"""命令行入口，由各平台层的 __main__ 调用。"""

from pathlib import Path

from glzh import diff, install, markup, string_tables, translations
from glzh.build import build
from glzh.game import GameFiles
from glzh.platform import Platform

REPO = Path(__file__).resolve().parents[2]
FILE_IN_USE = "有游戏文件被占用（{0}）。请退出游戏和正在扫描它的程序后重新运行，重新运行会接着完成。"


def main(argv: list[str], platform: Platform) -> int:
    commands = {"validate": cmd_validate, "build": cmd_build, "diff": cmd_diff, "install": cmd_install, "restore": cmd_restore}
    if len(argv) < 1 or argv[0] not in commands:
        print(f"用法：{{{'|'.join(commands)}}}")
        return 2
    return commands[argv[0]](argv[1:], platform)


def cmd_validate(args: list[str], platform: Platform) -> int:
    """校验译文格式；本机装有游戏时，再核对占位符、标签等标记与英文原文一致，并列出明显比英文宽的译文。"""
    errors, warnings = translations.validate_dir(), []
    src = platform.game()
    if not errors and src.exists():
        english = string_tables.read_tables(src.english.read_bytes())
        errors = markup.markup_errors_dir(english)
        warnings = markup.width_warnings_dir(english)
    for err in errors:
        print(err)
    print("译文校验通过" if not errors else f"共 {len(errors)} 处错误")
    if warnings:
        # 只是提示：宽度是估算，放不放得下要进游戏看
        print("\n以下译文明显比英文宽，可能超出界面的框，请进游戏检查：")
        for w in warnings:
            print(w)
        print(f"共 {len(warnings)} 条宽度提示（不影响校验结果）")
    return 1 if errors else 0


def cmd_build(args: list[str], platform: Platform) -> int:
    """build <输出目录>：从本地游戏文件构建，写到输出目录，不改动游戏。"""
    if len(args) != 1:
        print("用法：build <输出目录>")
        return 2
    out = Path(args[0]).resolve()
    if out.is_relative_to(REPO):
        print("输出目录不能在仓库内：产物含游戏原始资源，不得提交（见 ADR 0002）")
        return 2
    src = platform.game()
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


def cmd_diff(args: list[str], platform: Platform) -> int:
    """diff [--write]：游戏更新后列出待译、待复核、废弃的条目；--write 把改动条目置 stale 写回。"""
    if args not in ([], ["--write"]):
        print("用法：diff [--write]")
        return 2
    # 只做格式校验：标记核对以当前英文为准，原文改动的条目正是这里要找出来的
    errors = translations.validate_dir()
    if errors:
        print("\n".join(errors))
        return 1
    diffs = diff_with_game(platform.game())
    if args == ["--write"]:
        for table, d in diffs.items():
            translations.save_table(translations.DEFAULT_DIR, table, d.updated)
    return 0


def cmd_install(args: list[str], platform: Platform) -> int:
    """install：备份原始文件并把汉化注入本地游戏，可重复运行。"""
    src = platform.game()
    if not src.exists():
        print(f"没有在 {src.data} 找到 Golden Lap。{platform.locate_hint}")
        return 1
    if problem := platform.preflight():
        print(problem)
        return 1
    print(f"游戏位置：{src.data}")
    print("译文覆盖情况（未翻译的条目显示英文）：")
    diff_with_game(src)
    print("正在备份并注入，ui 包较大，约需半分钟……")
    try:
        written = install.install(src, platform.backup_dir)
    except (install.AlreadyPatched, ValueError) as e:  # ValueError：构建发现游戏结构变了，游戏文件还没动
        print(e)
        return 1
    except PermissionError as e:
        print(FILE_IN_USE.format(e.filename))
        return 1
    for rel in written:
        print(f"已写入 {rel}")
    print(f"完成。原始文件备份在 {platform.backup_dir}。进入游戏，在设置的语言选项中选择“简体中文”。")
    return 0


def cmd_restore(args: list[str], platform: Platform) -> int:
    """restore：把游戏恢复到未汉化状态。"""
    src = platform.game()
    if not src.catalog.exists():
        print(f"没有在 {src.data} 找到 Golden Lap。{platform.locate_hint}")
        return 1
    if problem := platform.preflight():
        print(problem)
        return 1
    try:
        restored, skipped = install.restore(src, platform.backup_dir)
    except (install.NotInstalled, install.BackupIncomplete) as e:
        print(e)
        return 1
    except PermissionError as e:
        print(FILE_IN_USE.format(e.filename))
        return 1
    for rel in restored:
        print(f"已还原 {rel}")
    for rel in skipped:
        print(f"已跳过 {rel}（已被游戏更新或校验覆盖，本就是原版）")
    print("完成。游戏已恢复为未汉化状态，语言选项中的土耳其语也已恢复。")
    return 0
