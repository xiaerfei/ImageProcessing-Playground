#!/usr/bin/env python3
"""检查仓库里所有 Markdown 的相对链接与图片路径是否还指得到东西。

文档一改名、一挪目录,链接就会烂,而烂链接在 PDF 里表现为「点了没反应」,
不翻源码根本发现不了。每次重排文档后跑一次。

    python3 tools/check_doc_links.py            # 只报坏链接
    python3 tools/check_doc_links.py --verbose  # 连好的一起列出来

外部链接(http/https)、锚点(#...)、mailto 一律跳过 —— 这里只管仓库内的路径。
退出码:有坏链接时为 1,便于挂到 pre-commit 或 CI。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

REPO = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "node_modules", "build", "__pycache__"}

# [文字](路径) —— 行内式;前面带 ! 的是图片,同样要查
LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)>\s]+)>?(?:\s+\"[^\"]*\")?\s*\)")
# <img src="路径">
IMG_RE = re.compile(r"<img\b[^>]*?\bsrc=[\"']([^\"']+)[\"']", re.I)
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


def iter_markdown() -> list[Path]:
    out = []
    for p in REPO.rglob("*.md"):
        if any(part in SKIP_DIRS for part in p.relative_to(REPO).parts):
            continue
        out.append(p)
    return sorted(out)


def targets(md: Path) -> list[tuple[int, str]]:
    """抽出一篇里所有本地链接目标,带行号;跳过围栏代码块。"""
    found: list[tuple[int, str]] = []
    fence = None
    for lineno, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if fence is None:
                fence = marker[0] * len(marker)
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue
        for raw in LINK_RE.findall(line) + IMG_RE.findall(line):
            if raw.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            found.append((lineno, raw))
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true", help="连正常链接也列出来")
    args = ap.parse_args()

    total = bad = 0
    for md in iter_markdown():
        rel_md = md.relative_to(REPO)
        for lineno, raw in targets(md):
            total += 1
            path = unquote(raw.split("#", 1)[0])
            if not path:            # 纯锚点,前面已经滤过,这里兜底
                continue
            dest = (md.parent / path).resolve()
            ok = dest.exists()
            if not ok:
                bad += 1
                print(f"✗ {rel_md}:{lineno}  ->  {raw}")
            elif args.verbose:
                print(f"  {rel_md}:{lineno}  ->  {raw}")

    print(f"\n共 {total} 条仓库内链接,坏 {bad} 条。")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
