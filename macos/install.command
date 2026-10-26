#!/bin/bash
# Golden Lap 简体中文汉化：双击运行即可安装；游戏更新后再运行一次。
set -e
. "$(dirname "$0")/_env.sh"
PYTHONPATH="$DIR/src" "$VENV/bin/python" -m glzh install
