#!/usr/bin/env python3
"""把一个 PDF 拆成单页 PDF,一页一个文件。

    Python-Prototyping/.venv/bin/python tools/split_pdf_pages.py <PDF>
    Python-Prototyping/.venv/bin/python tools/split_pdf_pages.py <PDF> --pages 1-20,35
    Python-Prototyping/.venv/bin/python tools/split_pdf_pages.py <PDF> -o 某个目录

输出文件名按页码补零,如 page-001.pdf … page-661.pdf,在 Finder 里按名字排序就是原书顺序。

默认输出到 Documents/_archive/原文-<书名>-拆页/:这个目录被 .gitignore 忽略,
拆出来的几百个文件不会被误提交(第三方原书只在本地留存)。

依赖 pypdf(已在 Python-Prototyping/requirements.txt 里)。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    sys.exit("缺 pypdf → Python-Prototyping/.venv/bin/pip install pypdf")

REPO = Path(__file__).resolve().parent.parent


def parse_pages(spec: str, total: int) -> list[int]:
    """把 "1-20,35" 解析成从 1 开始的页码列表(保持书写顺序,去重)。"""
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
        else:
            start = end = int(part)
        if not (1 <= start <= end <= total):
            sys.exit(f"页码范围 {part} 不对:这本只有 1~{total} 页")
        pages.extend(p for p in range(start, end + 1) if p not in pages)
    return pages


def main() -> None:
    ap = argparse.ArgumentParser(description="把 PDF 拆成单页 PDF")
    ap.add_argument("pdf", type=Path, help="要拆的 PDF")
    ap.add_argument("-o", "--out", type=Path, help="输出目录(默认 Documents/_archive/原文-<书名>-拆页/)")
    ap.add_argument("--pages", help="只拆这些页,如 1-20,35;不写 = 全部")
    args = ap.parse_args()

    if not args.pdf.is_file():
        sys.exit(f"找不到文件:{args.pdf}")

    reader = PdfReader(args.pdf)
    total = len(reader.pages)
    pages = parse_pages(args.pages, total) if args.pages else list(range(1, total + 1))

    out = args.out or REPO / "Documents" / "_archive" / f"原文-{args.pdf.stem}-拆页"
    out.mkdir(parents=True, exist_ok=True)

    width = len(str(total))  # 661 页 → 补到 3 位
    for n in pages:
        writer = PdfWriter()
        writer.add_page(reader.pages[n - 1])
        with open(out / f"page-{n:0{width}d}.pdf", "wb") as f:
            writer.write(f)

    print(f"共 {total} 页,拆出 {len(pages)} 页 → {out}")


if __name__ == "__main__":
    main()
