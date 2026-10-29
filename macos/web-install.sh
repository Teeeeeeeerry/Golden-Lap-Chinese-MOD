#!/bin/bash
# Golden Lap 简体中文汉化：一行命令安装或还原（见 docs/release-README.md）。
#   安装：/bin/bash -c "$(curl -fsSL https://github.com/Teeeeeeeerry/Golden-Lap-Chinese-MOD/releases/latest/download/install.sh)"
#   还原：/bin/bash -c "$(curl -fsSL https://github.com/Teeeeeeeerry/Golden-Lap-Chinese-MOD/releases/latest/download/install.sh)" glzh restore
# 用 curl 下载的文件不带隔离属性，所以不会被 macOS 拦截。不用 `curl | bash`：那样脚本占用标准输入，安装器结束时的 read 会读走脚本内容。
# 发布脚本生成本文件时，把 @ 占位符换成版本号和两个发布包的 sha256。
set -euo pipefail

VERSION="@VERSION@"
SHA256_arm64="@SHA256_arm64@"
SHA256_x86_64="@SHA256_x86_64@"
ROOT="GoldenLap-zh-Hans-v${VERSION}"
# 下载地址前缀可用环境变量覆盖，只供测试使用
BASE="${GLZH_DOWNLOAD_BASE:-https://github.com/Teeeeeeeerry/Golden-Lap-Chinese-MOD/releases/download/v${VERSION}}"
DEST="$HOME/Library/Application Support/GoldenLapZH/app/${VERSION}"

ACTION="${1:-install}"
case "$ACTION" in
  install | restore) ;;
  *)
    echo "用法：不带参数为安装，带 restore 为还原。"
    exit 2
    ;;
esac

# hw.optional.arm64 在 Apple 芯片上为 1，Rosetta 下也一样；Intel 上没有这一项。用绝对路径，不依赖 PATH
if [ "$(/usr/sbin/sysctl -n hw.optional.arm64 2>/dev/null)" = "1" ]; then ARCH=arm64; else ARCH=x86_64; fi
SHA256_VAR="SHA256_${ARCH}"
EXPECTED="${!SHA256_VAR}"
ZIP="${ROOT}-macos-${ARCH}.zip"

if [ ! -f "${DEST}/${ROOT}/${ACTION}.command" ]; then
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  echo "正在下载 Golden Lap 简体中文汉化 v${VERSION}（${ARCH}，约 40 MB）……"
  if ! /usr/bin/curl -fL --progress-bar -o "${TMP}/${ZIP}" "${BASE}/${ZIP}"; then
    echo "下载失败，请检查网络后重试。游戏没有被改动。"
    exit 1
  fi
  ACTUAL="$(/usr/bin/shasum -a 256 "${TMP}/${ZIP}" | cut -d ' ' -f 1)"
  if [ "$ACTUAL" != "$EXPECTED" ]; then
    echo "下载的文件校验不通过（sha256 不符），可能下载出错或被篡改。已停止，游戏没有被改动，请稍后重试。"
    exit 1
  fi
  echo "校验通过，正在解压……"
  /usr/bin/ditto -x -k "${TMP}/${ZIP}" "${TMP}/x"
  mkdir -p "$DEST"
  rm -rf "${DEST:?}/${ROOT}"
  mv "${TMP}/x/${ROOT}" "${DEST}/${ROOT}"
  rm -rf "$TMP"  # 下面 exec 换掉了本进程，EXIT trap 不会再执行，临时文件要先删
fi

exec /bin/bash "${DEST}/${ROOT}/${ACTION}.command"
