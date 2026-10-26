#!/bin/bash
# Golden Lap 简体中文汉化：双击运行即可把游戏恢复为未汉化状态。
set -e
. "$(dirname "$0")/_env.sh"
PYTHONPATH="$DIR/src" "$VENV/bin/python" -m glzh restore
