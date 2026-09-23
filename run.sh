#!/usr/bin/env bash
# 仓库根目录的 Python 入口 —— 固定用 Python-Prototyping/.venv 的解释器,
# 不用先 source activate,也不用自己 cd。
#
#   ./run.sh -l                                 列出所有可直接跑的脚本
#   ./run.sh 26                                 按文件名的片段找(gaussian 那个)
#   ./run.sh Ch03_Spatial_Filtering/26_gaussian_kernel_origin.py --show
#   ./run.sh figkit.py --help
#   ./run.sh -c "import cv2, numpy; print(cv2.__version__, numpy.__version__)"
#
# 脚本一律在「它自己所在的目录」里执行:GUIDE.md 里的示例写的是
# ../Assets/test-images/...,必须站在章节目录下才读得到。

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$ROOT/Python-Prototyping"
VENV="$WORKDIR/.venv"
PY="$VENV/bin/python"

die() { printf 'run.sh: %s\n' "$1" >&2; exit 1; }

usage() {
  sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

[ -x "$PY" ] || die "找不到 $PY
      先按 Python-Prototyping/README.md 建环境:
        python3 -m venv Python-Prototyping/.venv
        Python-Prototyping/.venv/bin/pip install -r Python-Prototyping/requirements.txt"

list_scripts() {
  ( cd "$WORKDIR" && find . -name '*.py' -not -path './.venv/*' -not -path '*/__pycache__/*' \
      | sed 's|^\./||' | sort )
}

case "${1:-}" in
  ""|-h|--help) usage; exit 0 ;;
  -l|--list)    list_scripts; exit 0 ;;
  -c|--code)
    shift
    [ $# -ge 1 ] || die "-c 后面要跟一段代码"
    cd "$WORKDIR"
    exec env PYTHONUNBUFFERED=1 "$PY" -c "$*"
    ;;
esac

target="$1"; shift

# 目标可以是:根目录下的相对路径 / 相对 Python-Prototyping 的路径 / 文件名片段
if [ -f "$target" ]; then
  script="$(cd -- "$(dirname -- "$target")" && pwd)/$(basename -- "$target")"
elif [ -f "$WORKDIR/$target" ]; then
  script="$WORKDIR/$target"
else
  matches="$(cd "$WORKDIR" && find . -name "*${target}*.py" -not -path './.venv/*' \
             | sed 's|^\./||' | sort)"
  [ -n "$matches" ] || die "找不到脚本:$target(用 ./run.sh -l 看全部)"
  if [ "$(printf '%s\n' "$matches" | wc -l | tr -d ' ')" -gt 1 ]; then
    printf 'run.sh: 「%s」匹配到多个,请写具体一点:\n%s\n' "$target" "$matches" >&2
    exit 2
  fi
  script="$WORKDIR/$matches"
fi

# 站在脚本自己的目录下执行,并把路径写成相对的 —— 和 README 里的用法一致,
# 报错时的 traceback 也短,不会拖一长串绝对路径。
cd -- "$(dirname -- "$script")"
exec env PYTHONUNBUFFERED=1 "$PY" "$(basename -- "$script")" "$@"
