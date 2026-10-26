#!/bin/bash
# Golden Lap 简体中文汉化：双击运行即可安装；游戏更新后再运行一次。
set -e
ENV_SH="$(dirname "$0")/_env.sh"
if [ ! -f "$ENV_SH" ]; then
  echo "缺少 _env.sh，请重新完整解压发布包后再运行。"
  read -r -p "按回车键关闭窗口……" _
  exit 1
fi
. "$ENV_SH"
PYTHONPATH="$DIR/src" "$VENV/bin/python" -m glzh install
