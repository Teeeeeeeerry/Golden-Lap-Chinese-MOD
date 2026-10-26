#!/bin/bash
# Golden Lap 简体中文汉化：双击运行即可安装；游戏更新后再运行一次。
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
# 发布包里脚本与 src/ 同级；在仓库中运行时脚本位于 macos/ 下
[ -d "$DIR/src" ] || DIR="$(dirname "$DIR")"
HOME_DIR="$HOME/Library/Application Support/GoldenLapZH"
VENV="$HOME_DIR/venv"

finish() { echo; read -r -p "按回车键关闭窗口……" _; }
trap finish EXIT

# 解除下载文件的隔离属性，免得后续脚本被 Gatekeeper 拦截
xattr -dr com.apple.quarantine "$DIR" 2>/dev/null || true

# 依赖要求 Python 3.11 及以上；系统自带的 python3 往往是 3.9
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3 /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    PYTHON="$(command -v "$candidate")"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  echo "需要 Python 3.11 或更新版本。请从 https://www.python.org/downloads/macos/ 下载安装后，再双击本文件。"
  exit 1
fi

# 首次运行在用户目录建独立的虚拟环境并安装锁定版本的依赖；requirements 变化时重装
mkdir -p "$HOME_DIR"
if [ ! -x "$VENV/bin/python" ] || ! cmp -s "$DIR/requirements.txt" "$VENV/requirements.txt"; then
  echo "首次运行，正在准备运行环境（需联网，约 1 分钟）……"
  rm -rf "$VENV"
  "$PYTHON" -m venv "$VENV"
  "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check -r "$DIR/requirements.txt"
  cp "$DIR/requirements.txt" "$VENV/requirements.txt"
fi

PYTHONPATH="$DIR/src" "$VENV/bin/python" -m glzh install
