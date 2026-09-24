#!/usr/bin/env python3
"""检查仓库里所有 Markdown 的相对链接与图片路径是否还指得到东西。

文档一改名、一挪目录,链接就会烂,而烂链接在 PDF 里表现为「点了没反应」,
不翻源码根本发现不了。每次重排文档后跑一次。

    python3 tools/check_doc_links.py            # 只报坏链接
    python3 tools/check_doc_links.py --verbose  # 连好的一起列出来

查两样东西:
  ① 路径 —— 文件/图片还在不在
  ② 锚点 —— #后面那段能不能对上目标文档里的某个标题

外部链接(http/https)、mailto 跳过。指向非 .md 的锚点只查文件存在,不查锚点
(那得解析 HTML,不值当)。
退出码:有坏链接时为 1,便于挂到 pre-commit 或 CI。

⚠️ 锚点为什么值得单独查:标题一改字、一换节,锚点就悄悄烂掉,
而它在 GitHub 上表现为「点了停在原地」,在 PDF 里表现为「点了没反应」——
两边都不报错,不翻源码根本发现不了。这条检查就是我自己写错一次之后补的:
曾经在 03-sharpening.md 里写 #二高斯滤波,可那是 02-smoothing.md 的节。

slug 规则按 GitHub 来(去掉格式标记 → 转小写 → 删标点 → 空格转连字符),
PDF 那边 pandoc 的规则与它在中文标题上基本一致。
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

REPO = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "node_modules", "build", "__pycache__"}

# [文字](路径) —— 行内式;前面带 ! 的是图片,同样要查
LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)>\s]+)>?(?:\s+\"[^\"]*\")?\s*\)")
# <img src="路径">
IMG_RE = re.compile(r"<img\b[^>]*?\bsrc=[\"']([^\"']+)[\"']", re.I)
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
# 文档里手写的 <a id="x"> / <a name="x"> 也算数
HTML_ANCHOR_RE = re.compile(r"<a\b[^>]*?\b(?:id|name)=[\"\']([^\"\']+)[\"\']", re.I)


def slugify(title: str) -> str:
    """把标题转成 GitHub 那样的锚点。

    顺序要紧:**先删标点,再把空格换成连字符**。
    「9. 附录:最小可运行 C 示例」这种标题,先删掉 `.` 和 `:` 才会得到
    #9-附录最小可运行-c-示例;反过来做会多出几个连字符。
    """
    t = title
    t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", t)   # [文字](链接) 只留文字
    t = re.sub(r"[`*_~]", "", t)                        # 去掉行内格式标记
    t = t.lower()
    # 删掉标点(P*)和符号(S*,含 emoji);字母、数字、空格、连字符、下划线留下
    t = "".join(c for c in t
                if c in " -_" or unicodedata.category(c)[0] not in "PSCZ")
    return re.sub(r"\s+", "-", t.strip())


def anchors_of(md: Path) -> set[str]:
    """一篇文档提供的所有锚点。重名标题按 GitHub 的办法加 -1、-2。"""
    out: set[str] = set()
    seen: dict[str, int] = {}
    fence = None
    for line in md.read_text(encoding="utf-8").splitlines():
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
        out.update(HTML_ANCHOR_RE.findall(line))
        h = HEADING_RE.match(line)
        if h:
            base = slugify(h.group(2))
            if not base:
                continue
            n = seen.get(base, 0)
            seen[base] = n + 1
            out.add(base if n == 0 else f"{base}-{n}")
    return out


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
            if raw.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            found.append((lineno, raw))
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true", help="连正常链接也列出来")
    args = ap.parse_args()

    cache: dict[Path, set[str]] = {}

    def anchors(p: Path) -> set[str]:
        if p not in cache:
            cache[p] = anchors_of(p)
        return cache[p]

    total = bad = n_anchor = bad_anchor = 0
    for md in iter_markdown():
        rel_md = md.relative_to(REPO)
        for lineno, raw in targets(md):
            path_part, _, frag = raw.partition("#")
            path = unquote(path_part)
            frag = unquote(frag)

            dest = (md.parent / path).resolve() if path else md
            if path:
                total += 1
                if not dest.exists():
                    bad += 1
                    print(f"✗ {rel_md}:{lineno}  路径不存在  ->  {raw}")
                    continue
                if args.verbose:
                    print(f"  {rel_md}:{lineno}  ->  {raw}")

            # 锚点:只有目标是 .md 才查得动
            if frag and dest.suffix.lower() == ".md" and dest.exists():
                n_anchor += 1
                if frag not in anchors(dest):
                    bad_anchor += 1
                    near = sorted(anchors(dest))[:3]
                    print(f"✗ {rel_md}:{lineno}  锚点对不上  ->  {raw}")
                    print(f"    {dest.relative_to(REPO)} 里没有 #{frag};"
                          f"该文件的锚点形如 {', '.join('#' + a for a in near)} …")
                elif args.verbose and not path:
                    print(f"  {rel_md}:{lineno}  ->  {raw}")

    print(f"\n共 {total} 条仓库内链接,坏 {bad} 条;"
          f"{n_anchor} 条锚点,坏 {bad_anchor} 条。")
    return 1 if (bad or bad_anchor) else 0


if __name__ == "__main__":
    sys.exit(main())
