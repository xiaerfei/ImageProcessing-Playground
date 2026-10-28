#!/usr/bin/env bash
# 把上一级目录的译稿 md 逐个转成 tex/chapters/*.tex。
# 用法：bash tex/build-tex.sh          只转换
#       bash tex/build-tex.sh --pdf    转换后再用 xelatex 编出 tex/main.pdf
set -euo pipefail

TEX_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$(dirname "$TEX_DIR")"
OUT_DIR="$TEX_DIR/chapters"
mkdir -p "$OUT_DIR"

# 图片路径写的是 assets/...，要在 md 所在目录运行 pandoc 才能读到图片尺寸
cd "$SRC_DIR"
for md in [0-9][0-9]*-DSP指南-*.md; do
  id="${md%%-*}"
  [ "$id" = "00a" ] && continue # 目录由 \tableofcontents 自动生成
  extra=()
  [ "$id" = "35" ] && extra=(-M chaptitle=索引)
  pandoc "$md" \
    -f markdown-implicit_figures-auto_identifiers-implicit_header_references \
    -t latex \
    --top-level-division=chapter \
    --lua-filter "$TEX_DIR/md2tex.lua" \
    -M fileid="$id" ${extra[@]+"${extra[@]}"} \
    -o "$OUT_DIR/$id.tex"
  # 让 VS Code 在章节文件里也能直接编译整本书
  printf '%% !TEX root = ../main.tex\n%% 本文件由 build-tex.sh 从 %s 生成，改内容请改 md 后重新生成\n\n' "$md" \
    | cat - "$OUT_DIR/$id.tex" > "$OUT_DIR/$id.tmp" && mv "$OUT_DIR/$id.tmp" "$OUT_DIR/$id.tex"
  echo "  $md → chapters/$id.tex"
done

if [ "${1:-}" = "--pdf" ]; then
  cd "$TEX_DIR"
  # 两遍：第一遍生成目录与交叉引用，第二遍填进去
  for _ in 1 2; do
    xelatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null
  done
  echo "已生成 $TEX_DIR/main.pdf"
fi
