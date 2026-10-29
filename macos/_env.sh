# install.command 与 restore.command 共用：定位项目目录、解除隔离属性、找到要用的 Python。
# 调用方需先 set -e；之后可使用 $DIR 与 $PY。
DIR="$(cd "$(dirname "$0")" && pwd)"
# 发布包里脚本与 src/ 同级；在仓库中运行时脚本位于 macos/ 下
[ -d "$DIR/src" ] || DIR="$(dirname "$DIR")"
HOME_DIR="$HOME/Library/Application Support/GoldenLapZH"

finish() { echo; read -r -p "按回车键关闭窗口……" _ || true; }  # 没有终端输入时（如被脚本调用）直接结束
trap finish EXIT

# 解除下载文件的隔离属性，免得后续脚本和内置 Python 被 Gatekeeper 逐个拦截；必须在运行内置 Python 之前
xattr -dr com.apple.quarantine "$DIR" 2>/dev/null || true

# 发布包自带运行环境（ADR 0007）：不用系统 Python，不建虚拟环境，也不联网
PY="$DIR/runtime/python/bin/python3.12"
if [ -x "$PY" ]; then
  export PYTHONNOUSERSITE=1  # 不让玩家自己装的 Python 包混进来
else
  # 在仓库里运行（没有内置运行环境）：依赖要求 Python 3.11 及以上；系统自带的 python3 往往是 3.9
  VENV="$HOME_DIR/venv"
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
    echo "正在准备运行环境（需联网，约 1 分钟）……"
    rm -rf "$VENV"
    "$PYTHON" -m venv "$VENV"
    "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check -r "$DIR/requirements.txt"
    cp "$DIR/requirements.txt" "$VENV/requirements.txt"
  fi
  PY="$VENV/bin/python"
fi
