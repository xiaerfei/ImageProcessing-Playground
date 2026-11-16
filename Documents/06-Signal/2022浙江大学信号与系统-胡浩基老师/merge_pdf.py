#!/usr/bin/env python3
"""把本目录按编号命名的笔记 PDF（00-xxx.pdf、01-xxx.pdf……）合并成一个 PDF。

用法（在任意目录执行都行）：
    python3 merge_pdf.py                 合并全部，输出到本目录的「信号与系统听课笔记合集.pdf」
    python3 merge_pdf.py -o 合集.pdf      指定输出文件
    python3 merge_pdf.py 03 06           只合并文件名里含 03 或 06 的
    python3 merge_pdf.py --build         先用 build_pdf.py 重新编译过期的 .tex，再合并

合并结果带 PDF 书签：每篇一个顶层书签（如「13 典型信号的傅里叶变换」），
原来各篇自己的章节书签挂在它下面，点击仍能跳到对应页。

只收文件名以两位数字加「-」开头的 PDF，按编号排序；没有编号的旧文件（如「典型的信号.pdf」）
和合并结果本身不会被收进去。.tex 比对应的 .pdf 新时会提示，加 --build 可以先重新编译。

合并用 macOS 自带的 PDFKit（通过 swift 运行一小段代码），不需要装 Python 包；
没有 swift（未装 Xcode 或命令行工具）时退回到 poppler 的 pdfunite（brew install poppler），
这种情况下不带书签。

只用 Python 标准库，兼容 macOS 自带的 Python 3.9。
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = "信号与系统听课笔记合集.pdf"
NUMBERED = re.compile(r"^(\d{2})-(.+)\.pdf$")

# 用 PDFKit 合并：先把每篇的书签读成「标题 + 页码 + 页内位置」，再把页面依次插入新文档，
# 最后按新页码重建书签。参数：输出路径、文档标题，之后每两个一组为「PDF 路径、顶层书签标题」。
SWIFT_SRC = r"""
import Foundation
import PDFKit

struct Mark { let label: String; let page: Int; let point: CGPoint?; let children: [Mark] }

func readMarks(_ item: PDFOutline, _ doc: PDFDocument) -> [Mark] {
    var out: [Mark] = []
    for i in 0..<item.numberOfChildren {
        guard let c = item.child(at: i) else { continue }
        let dest = c.destination ?? (c.action as? PDFActionGoTo)?.destination
        var page = -1
        var point: CGPoint? = nil
        if let d = dest, let p = d.page {
            page = doc.index(for: p)
            point = d.point
        }
        out.append(Mark(label: c.label ?? "", page: page, point: point, children: readMarks(c, doc)))
    }
    return out
}

func addMarks(_ marks: [Mark], to parent: PDFOutline, in doc: PDFDocument, offset: Int) {
    for m in marks {
        let item = PDFOutline()
        item.label = m.label
        if m.page >= 0, let p = doc.page(at: offset + m.page) {
            item.destination = PDFDestination(page: p, at: m.point ?? CGPoint(x: 0, y: p.bounds(for: .mediaBox).height))
        }
        parent.insertChild(item, at: parent.numberOfChildren)
        addMarks(m.children, to: item, in: doc, offset: offset)
    }
}

let args = CommandLine.arguments
let outPath = args[1]
let title = args[2]
let merged = PDFDocument()
let root = PDFOutline()
var pending: [(String, Int, [Mark])] = []

var i = 3
while i + 1 < args.count {
    let path = args[i], label = args[i + 1]
    i += 2
    guard let src = PDFDocument(url: URL(fileURLWithPath: path)) else {
        FileHandle.standardError.write("打不开：\(path)\n".data(using: .utf8)!)
        exit(1)
    }
    let marks = src.outlineRoot.map { readMarks($0, src) } ?? []
    let offset = merged.pageCount
    for p in 0..<src.pageCount {
        if let page = src.page(at: p) { merged.insert(page, at: merged.pageCount) }
    }
    pending.append((label, offset, marks))
}

for (label, offset, marks) in pending {
    let top = PDFOutline()
    top.label = label
    if let p = merged.page(at: offset) {
        top.destination = PDFDestination(page: p, at: CGPoint(x: 0, y: p.bounds(for: .mediaBox).height))
    }
    root.insertChild(top, at: root.numberOfChildren)
    addMarks(marks, to: top, in: merged, offset: offset)
}
merged.outlineRoot = root
merged.documentAttributes = [PDFDocumentAttribute.titleAttribute: title]
if !merged.write(to: URL(fileURLWithPath: outPath)) {
    FileHandle.standardError.write("写入失败：\(outPath)\n".data(using: .utf8)!)
    exit(1)
}
print(merged.pageCount)
"""


def say(msg=""):
    print(msg, flush=True)


def collect(filters, out_name):
    """返回 [(编号, PDF 文件名, 书签标题)]，按编号排序。"""
    items = []
    for name in os.listdir(HERE):
        m = NUMBERED.match(name)
        if not m or name == out_name:
            continue
        if filters and not any(f in name for f in filters):
            continue
        items.append((m.group(1), name, f"{m.group(1)} {m.group(2)}"))
    return sorted(items)


def stale_tex(filters):
    """返回需要重新编译的 .tex：没有 PDF，或 .tex 比 PDF 新。"""
    out = []
    for name in sorted(os.listdir(HERE)):
        if not (name.endswith(".tex") and re.match(r"^\d{2}-", name)):
            continue
        if filters and not any(f in name for f in filters):
            continue
        tex = os.path.join(HERE, name)
        pdf = tex[:-4] + ".pdf"
        if not os.path.exists(pdf) or os.path.getmtime(tex) > os.path.getmtime(pdf):
            out.append(name)
    return out


def merge_with_swift(swift, out_path, title, items):
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "merge.swift")
        with open(src, "w", encoding="utf-8") as f:
            f.write(SWIFT_SRC)
        cmd = [swift, src, out_path, title]
        for _, name, label in items:
            cmd += [os.path.join(HERE, name), label]
        r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("swift 合并失败：\n" + (r.stderr or r.stdout).strip())
    return r.stdout.strip().splitlines()[-1]


def find_swift():
    swift = shutil.which("swift")
    if swift:
        return swift
    try:
        r = subprocess.run(["xcrun", "--find", "swift"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except OSError:
        pass
    return None


def main():
    ap = argparse.ArgumentParser(description="把本目录按编号命名的笔记 PDF 合并成一个。")
    ap.add_argument("filters", nargs="*", help="只合并文件名含这些字符串的（如 03 06），不给则全部")
    ap.add_argument("-o", "--out", default=DEFAULT_OUT, help=f"输出文件（默认本目录的 {DEFAULT_OUT}）")
    ap.add_argument("--title", default="信号与系统听课笔记（浙江大学 2022，胡浩基）", help="合并后 PDF 的文档标题")
    ap.add_argument("--build", action="store_true", help="先用 build_pdf.py 重新编译过期或缺 PDF 的 .tex")
    a = ap.parse_args()

    out_path = a.out if os.path.isabs(a.out) else os.path.join(HERE, a.out)
    out_name = os.path.basename(out_path)

    stale = stale_tex(a.filters)
    if stale and a.build:
        say(f"先重新编译 {len(stale)} 个 .tex……")
        keys = [n[:2] for n in stale]
        r = subprocess.run([sys.executable, os.path.join(HERE, "build_pdf.py"), *keys])
        if r.returncode != 0:
            sys.exit("编译失败，没有合并。")
    elif stale:
        say("提示：下面这些 .tex 比 PDF 新或还没有 PDF，合并的是旧版（加 --build 先重新编译）：")
        for n in stale:
            say(f"  {n}")

    items = collect(a.filters, out_name)
    if not items:
        sys.exit("没有找到可合并的 PDF（文件名需以「两位数字-」开头）。")

    say(f"合并 {len(items)} 个 PDF：")
    for num, name, _ in items:
        say(f"  {name}")

    swift = find_swift()
    if swift:
        pages = merge_with_swift(swift, out_path, a.title, items)
        say(f"完成：{out_path}（{pages} 页，带书签）")
    elif shutil.which("pdfunite"):
        cmd = ["pdfunite", *[os.path.join(HERE, n) for _, n, _ in items], out_path]
        if subprocess.run(cmd).returncode != 0:
            sys.exit("pdfunite 合并失败。")
        say(f"完成：{out_path}（用 pdfunite 合并，不带书签）")
    else:
        sys.exit("找不到 swift，也找不到 pdfunite：装 Xcode 命令行工具（xcode-select --install）"
                 "或 brew install poppler 后再试。")


if __name__ == "__main__":
    main()
