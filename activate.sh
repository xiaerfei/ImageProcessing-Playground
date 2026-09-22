#!/usr/bin/env bash
# 在仓库根目录激活 Python-Prototyping/.venv:
#
#     . ./activate.sh          # source ./activate.sh 也行,但多打字
#
# 必须 source,不能 ./activate.sh 执行 —— activate 改的是当前 shell 的
# PATH / VIRTUAL_ENV,子进程里改完就随进程一起没了,出来还是老样子。
# 退出用 deactivate(venv 自带的,不归这个脚本管)。
#
# 换行一下也能用:cd 到根目录敲 . ./activate.sh 即可,venv 再深也不用手打。

# zsh 里 $0 就是被 source 的文件(default 的 FUNCTION_ARGZERO),
# bash 里得读 BASH_SOURCE,所以两个 shell 分开取。
if [ -n "${ZSH_VERSION:-}" ]; then
  _ipa_self="$0"
  case "${ZSH_EVAL_CONTEXT:-}" in
    *:file*) ;;                       # toplevel:file = 被 source
    *) printf '要 source 才有用:. ./activate.sh\n' >&2; exit 1 ;;
  esac
else
  _ipa_self="${BASH_SOURCE[0]}"
  if [ "$_ipa_self" = "$0" ]; then    # 相等 = 是执行,不是 source
    printf '要 source 才有用:. ./activate.sh\n' >&2
    exit 1
  fi
fi

_ipa_venv="$(cd -- "$(dirname -- "$_ipa_self")" && pwd)/Python-Prototyping/.venv"

if [ ! -f "$_ipa_venv/bin/activate" ]; then
  printf '找不到 %s\n先建环境:python3 -m venv Python-Prototyping/.venv\n' \
    "$_ipa_venv/bin/activate" >&2
  # 不能用 exit:source 进来时 exit 会把整个终端关掉
  unset _ipa_self _ipa_venv
  return 1 2>/dev/null || true
fi

if [ "${VIRTUAL_ENV:-}" = "$_ipa_venv" ]; then
  printf 'venv 已经在了:%s\n' "$_ipa_venv"       # 再 source 一次会把 PATH 顶重复
else
  if [ -n "${VIRTUAL_ENV:-}" ] && type deactivate >/dev/null 2>&1; then
    deactivate                                    # 从别的 venv 切过来,先摘旧的
  fi
  . "$_ipa_venv/bin/activate"
  printf 'venv   %s\npython %s\n' "${VIRTUAL_ENV}" "$(command -v python)"
fi

unset _ipa_self _ipa_venv
