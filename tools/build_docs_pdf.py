#!/usr/bin/env python3
"""把 Documents/ 下的 Markdown 学习笔记按"序号顺序"合并成一份带书签目录的 PDF。

脚本做的事(文档增删后重跑一次即可,不需要改任何配置):

  1. 扫描 Documents/,按目录名/文件名的**数字前缀**自然排序,收集所有 .md
     (默认跳过 _archive/,那是原始对话记录,不是笔记)
  2. 用 pandoc 逐篇转成 HTML 片段,顺手做四件事:
       - 把图片内联成 data URI,最终 HTML 自包含,不依赖相对路径
       - 给每个标题生成稳定唯一的锚点,供目录页与跨篇链接跳转
       - 把 "you asked / gemini response" 这类当分隔符用的假标题降级成粗体
       - 重排标题层级,使"分组 → 篇 → 节"在书签里自然成树
  3. 汇总所有标题,生成可点击跳转的目录页
  4. 拼接成一个自包含 HTML
  5. 交给 Chrome headless 打印 PDF,并用 --generate-pdf-document-outline 生成书签

21 篇 / 283 页的实测耗时约 10 秒(pandoc 2s,拼装 <0.1s,Chrome 打印 ~8s)。

两个踩过的坑,已经在代码里绕开:
  - headless Chrome 打印完 PDF 后经常**不退出进程**(PDF 7 秒就写完了,进程却一直挂着),
    所以 html_to_pdf() 不等它结束,而是盯着输出文件"写稳"了就主动收掉它;
  - 接管道时 stdout 是块缓冲的,进度会被憋住,所以统一用 log() 输出并 flush。

依赖(本机已具备):
  - pandoc       brew install pandoc
  - Google Chrome(或 Chromium)
  - pypdf        可选,仅用于自检生成的书签数量

用法:
  python3 tools/build_docs_pdf.py              # 生成 Documents/build/图像处理学习笔记.pdf
  python3 tools/build_docs_pdf.py --open       # 生成后顺便打开
  python3 tools/build_docs_pdf.py --keep-html  # 保留中间 HTML(相当于一份网页版合集)
  python3 tools/build_docs_pdf.py --list       # 只打印成书顺序,不转换
  python3 tools/build_docs_pdf.py --toc-depth 3   # 目录页也展开到节(会更长)

输出目录 Documents/build/ 已被仓库 .gitignore 里的 build/ 规则忽略。
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCS_DIR = REPO_ROOT / "Documents"
DEFAULT_TITLE = "数字图像处理 · 学习笔记合集"


def log(msg: str = "") -> None:
    """带 flush 的输出:stdout 接管道时是块缓冲的,不 flush 就看不到进度。"""
    print(msg, flush=True)


# ============================================================== 配置表 ======
# 下面三张表是唯一需要"手工维护"的地方,而且都不是必须的。

# 不参与成书的分组(外部参考代码等)
DEFAULT_EXCLUDE_DIRS = {"_archive", "build"}

# 分组展示名;没写的就按"目录名去掉数字前缀"原样用
GROUP_TITLES = {
    "": "总览 · 先读这一篇",
    "00-roadmap": "学习路线与全书地图",
    "01-fundamentals": "图像基础",
    "02-intensity": "亮度与灰度",
    "03-histogram": "直方图",
    "04-geometry": "几何变换",
    "05-spatial-filtering": "空间滤波",
}

# 相对路径 → 篇名覆盖(一般不用写,自动推断已经很准)
TITLE_OVERRIDES = {
    "README.md": "如何使用这套笔记",
}

# 被当成"分隔符"而不是真标题的写法(整理自 Gemini 对话记录)
NOISE_HEADING_RE = re.compile(
    r"^\s*(you asked|gemini response|assistant|user|你问|我说|回答|提问)\s*[:：]?\s*$",
    re.I,
)
NOISE_REPEAT_MIN = 3       # 同一篇内重复出现这么多次的短标题 → 判为分隔符
NOISE_REPEAT_MAX_LEN = 24  # 只对短标题套用上面这条


# ============================================================== 数据结构 ===


@dataclass
class Heading:
    """一行标题。line 为所在行号,level 为原 Markdown 级别(1~6)。"""

    line: int
    level: int
    text: str


@dataclass
class Doc:
    """一篇笔记。"""

    path: Path
    rel: Path              # 相对 Documents/ 的路径
    index: int             # 全局顺序(从 1 开始)
    group: str             # 所属分组目录名(根目录下的散篇用 "")
    title: str = ""
    headings: list[Heading] = field(default_factory=list)
    shift: int = 1             # 标题层级整体下移量
    title_line: int = -1       # 被当作篇名的那个 H1 行号(-1 表示篇名来自文件名)
    dehead_lines: set[int] = field(default_factory=set)
    lines: list[str] = field(default_factory=list)
    fragment: str = ""         # pandoc 产出的 HTML 片段(图片已内联)

    @property
    def anchor(self) -> str:
        return f"doc{self.index}-top"


# ============================================================== 排序工具 ===


def _chunks(text: str) -> tuple[Any, ...]:
    """把 '01-foo2' 拆成可比较的块,数字按数值比,文字按字典序比。"""
    out = []
    for part in re.split(r"(\d+)", text.lower()):
        if not part:
            continue
        out.append((0, int(part), "") if part.isdigit() else (1, 0, part))
    return tuple(out)


def sort_key(path: Path) -> tuple[Any, ...]:
    """按路径逐级自然排序:先看数字前缀,再看名字。"""
    return tuple(_chunks(part) for part in path.parts)


# ============================================================== Markdown ===

_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^( {0,3})(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
_ATTR_RE = re.compile(r"\s*\{(?:[#.][^}]*)\}\s*$")
_MD_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_IMG_SRC_RE = re.compile(r"(<img\b[^>]*?\bsrc=\")([^\"]+)(\")", re.I)

# pandoc 会给每个高亮代码块加行号锚点,PDF 里既没用又会造成 id 重名
_LINE_ANCHOR_RE = re.compile(r'<a href="#cb\d+-\d+" aria-hidden="true" tabindex="-1"></a>')
_SPAN_CB_RE = re.compile(r'<span id="cb\d+-\d+">')
_CB_ID_RE = re.compile(r'id="cb(\d+)"')


def tidy_fragment(fragment: str, index: int) -> str:
    """去掉代码块的行号锚点,并把 pandoc 的 cbN 序号变成全局唯一。"""
    fragment = _LINE_ANCHOR_RE.sub("", fragment)
    fragment = _SPAN_CB_RE.sub("<span>", fragment)
    return _CB_ID_RE.sub(lambda m: f'id="doc{index}-cb{m.group(1)}"', fragment)


def scan_headings(lines: list[str]) -> list[Heading]:
    """扫出所有 ATX 标题;自动跳过围栏代码块和 HTML 注释。"""
    heads: list[Heading] = []
    fence = None
    in_comment = False

    for i, line in enumerate(lines):
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if "<!--" in line and "-->" not in line:
            in_comment = True
            continue

        m = _FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if fence is None:
                fence = marker[0] * len(marker)
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue

        h = _HEADING_RE.match(line)
        if h:
            heads.append(Heading(i, len(h.group(2)), h.group(3).strip()))
    return heads


def strip_attrs(text: str) -> str:
    return _ATTR_RE.sub("", text).strip()


def derive_title(doc: Doc, first_h1: Heading | None) -> tuple[str, int]:
    """篇名推断:覆盖表 → 第一个像样的 H1 → 文件名。返回 (篇名, 用作篇名的行号)。"""
    override = TITLE_OVERRIDES.get(doc.rel.as_posix())
    if override:
        return override, first_h1.line if first_h1 else -1

    if first_h1 and not NOISE_HEADING_RE.match(first_h1.text):
        return strip_attrs(first_h1.text), first_h1.line

    stem = re.sub(r"^\d+[-_]\s*", "", doc.path.stem)
    return stem.replace("-", " ").replace("_", " ").strip(), -1


def find_noise_lines(headings: list[Heading]) -> set[int]:
    """找出应该降级成粗体的"假标题"行号。"""
    noise = {h.line for h in headings if NOISE_HEADING_RE.match(h.text)}

    counts: dict[str, int] = {}
    for h in headings:
        key = strip_attrs(h.text)
        counts[key] = counts.get(key, 0) + 1
    for h in headings:
        key = strip_attrs(h.text)
        if counts[key] >= NOISE_REPEAT_MIN and len(key) <= NOISE_REPEAT_MAX_LEN:
            noise.add(h.line)
    return noise


def rewrite_md_links(text: str, base_dir: Path, anchor_by_path: dict[Path, str]) -> str:
    """把指向其它笔记的链接改成内部锚点,PDF 里点一下就能跳过去。"""

    def repl(m: re.Match[str]) -> str:
        label, target = m.group(1), m.group(2)
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
            return m.group(0)
        path_part = target.split("#", 1)[0]
        if not path_part.lower().endswith(".md"):
            return m.group(0)
        try:
            resolved = (base_dir / unquote(path_part)).resolve()
        except OSError:
            return m.group(0)
        anchor = anchor_by_path.get(resolved)
        return f"[{label}](#{anchor})" if anchor else m.group(0)

    return _MD_LINK_RE.sub(repl, text)


def escape_emphasis(text: str) -> str:
    """转义标题里裸露的 * 和 _(代码跨度内的不动)。

    为什么要做这一步:pandoc 的标题属性写法 `## 标题 {#id}` 是在行内解析完之后才认的,
    标题里只要出现一个配不上对的 * 或 _(例如 `Lab 的 L*` `_archive`),
    行内解析器就会把后面的 `{#id}` 一起吞进未闭合的强调里,属性失效 ——
    表现为 PDF 书签上直接印出 `{#doc8-h385}` 这一串。
    标题里我们从不用 **加粗** 或 _斜体_,所以一律转义是安全的。
    """
    out, in_code = [], False
    for ch in text:
        if ch == "`":
            in_code = not in_code
        elif ch in "*_" and not in_code:
            out.append("\\")
        out.append(ch)
    return "".join(out)


def transform_markdown(doc: Doc, anchor_by_path: dict[Path, str]) -> str:
    """重排标题层级、降级假标题、改写跨篇链接,产出喂给 pandoc 的 Markdown。"""
    by_line = {h.line: h for h in doc.headings}
    out: list[str] = []

    for i, line in enumerate(doc.lines):
        h = by_line.get(i)
        if h is None:
            out.append(line)
            continue

        text = strip_attrs(h.text)
        if i == doc.title_line:            # 篇名行交给外层 <h2>,正文里不再重复
            continue
        if i in doc.dehead_lines:
            out.append(f"**{text}**")
            continue

        level = min(h.level + doc.shift, 6)
        out.append(f"{'#' * level} {escape_emphasis(text)} {{#doc{doc.index}-h{i}}}")

    body = rewrite_md_links("\n".join(out), doc.path.parent, anchor_by_path)
    return body


# ============================================================== 图片内联 ===

_mime_cache: dict[str, str | None] = {}


def _data_uri(path: Path, warn: list[str]) -> str | None:
    if path.suffix.lower() not in _mime_cache:
        _mime_cache[path.suffix.lower()] = mimetypes.guess_type(path.name)[0]
    mime = _mime_cache[path.suffix.lower()] or "application/octet-stream"
    try:
        raw = path.read_bytes()
    except OSError as exc:
        warn.append(f"图片读取失败 {path}: {exc}")
        return None
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def inline_images(fragment: str, base_dir: Path, warn: list[str]) -> str:
    """把 HTML 片段里的本地图片路径换成 data URI。"""

    def repl(m: re.Match[str]) -> str:
        src = html.unescape(m.group(2))
        if src.startswith(("data:", "http://", "https://")):
            return m.group(0)
        rel = unquote(src)
        if rel.startswith("file://"):
            rel = unquote(rel[len("file://"):])
        target = Path(rel if Path(rel).is_absolute() else (base_dir / rel)).resolve()
        if not target.is_file():
            warn.append(f"图片不存在 {target}")
            return m.group(0)
        uri = _data_uri(target, warn)
        return m.group(0) if uri is None else f"{m.group(1)}{uri}{m.group(3)}"

    return _IMG_SRC_RE.sub(repl, fragment)


# ============================================================== pandoc =====


def find_pandoc(explicit: str | None) -> str:
    exe = explicit or shutil.which("pandoc")
    if not exe:
        sys.exit("找不到 pandoc,请先安装:brew install pandoc")
    return exe


def pandoc_highlight_css(pandoc: str) -> str:
    """只取 pandoc 的代码高亮样式,不要它自带的那套页面布局(会把 A4 挤成一条)。"""
    probe = "```c\nint main(void) { return 0; }\n```\n"
    proc = subprocess.run(
        [pandoc, "-s", "--syntax-highlighting=tango", "-t", "html5", "-f", "markdown"],
        input=probe, capture_output=True, text=True,
    )
    m = re.search(r"<style>(.*?)</style>", proc.stdout, re.S)
    if not m:
        return ""
    css = m.group(1)
    marker = "/* CSS for syntax highlighting */"
    return css[css.index(marker):] if marker in css else ""


def md_to_html(pandoc: str, markdown: str, math: str, workdir: Path, name: str) -> str:
    src = workdir / f"{name}.md"
    src.write_text(markdown, encoding="utf-8")

    cmd = [pandoc, "-f", "markdown", "-t", "html5", "--wrap=none", "-o", "-", str(src)]
    if math == "mathml":
        cmd.append("--mathml")
    elif math == "katex":
        cmd.append("--katex")

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"pandoc 转换失败({name}):\n{proc.stderr.strip()}")
    return proc.stdout


# ============================================================== 收集文档 ===


def iter_groups(docs_dir: Path, excludes: set[str]) -> list[tuple[str, list[Path]]]:
    """按阅读顺序列出 (分组名, [md 路径])。数字前缀决定顺序,根目录散篇排最前。"""
    groups: list[tuple[str, list[Path]]] = []
    # 根目录下的散篇(README 之类)当成第一个分组 ""
    root_mds = sorted(
        (p for p in docs_dir.glob("*.md") if p.is_file()),
        key=lambda p: sort_key(Path(p.name)),
    )
    if root_mds:
        groups.append(("", root_mds))

    for entry in sorted(docs_dir.iterdir(), key=lambda p: sort_key(Path(p.name))):
        if not entry.is_dir() or entry.name in excludes or entry.name.startswith("."):
            continue
        mds = sorted(
            (p for p in entry.rglob("*.md") if p.is_file()),
            key=lambda p: sort_key(p.relative_to(entry)),
        )
        if mds:
            groups.append((entry.name, mds))
    return groups


def load_docs(docs_dir: Path, groups: list[tuple[str, list[Path]]]) -> list[tuple[str, list[Doc]]]:
    """只做"读文件 → 扫标题 → 定篇名",不碰 pandoc(增量判断和 --list 都靠它)。"""
    plan: list[tuple[str, list[Doc]]] = []
    index = 0
    for group_name, paths in groups:
        docs: list[Doc] = []
        for path in paths:
            index += 1
            doc = Doc(path=path, rel=path.relative_to(docs_dir), index=index, group=group_name)
            doc.lines = path.read_text(encoding="utf-8").splitlines()
            doc.headings = scan_headings(doc.lines)
            first_h1 = next((h for h in doc.headings if h.level == 1), None)
            doc.title, doc.title_line = derive_title(doc, first_h1)
            docs.append(doc)
        plan.append((group_name, docs))
    return plan


def scan_docs(
    docs_dir: Path,
    pandoc: str,
    excludes: set[str],
    math: str,
    workdir: Path,
    jobs: int = 1,
) -> tuple[dict[str, list[Doc]], list[str]]:
    """按阅读顺序收集文档并逐篇转换,返回 ({分组名: [Doc]}, 警告列表)。"""
    plan = load_docs(docs_dir, iter_groups(docs_dir, excludes))
    anchor_by_path = {d.path.resolve(): d.anchor for _, docs in plan for d in docs}

    # 逐篇交给 pandoc。篇与篇互不依赖,可以并发
    all_docs = [doc for _, docs in plan for doc in docs]
    total = len(all_docs)

    def convert(doc: Doc) -> list[str]:
        """单篇转换,返回这篇自己的警告(避免多线程往同一个 list 里写)。"""
        local: list[str] = []
        doc.dehead_lines = find_noise_lines(doc.headings)
        extra_h1 = any(
            h.level == 1 and h.line not in doc.dehead_lines and h.line != doc.title_line
            for h in doc.headings
        )
        # 篇名占 h2;文档自身 H1 若另有其人,整体再多降一级,保证都挂在篇名下面
        doc.shift = 2 if extra_h1 else 1
        markdown = transform_markdown(doc, anchor_by_path)
        fragment = md_to_html(pandoc, markdown, math, workdir, f"doc{doc.index}")
        fragment = tidy_fragment(fragment, doc.index)
        doc.fragment = inline_images(fragment, doc.path.parent, local)
        return local

    warnings: list[str] = []
    if jobs > 1 and total > 1:
        with ThreadPoolExecutor(max_workers=min(jobs, total)) as pool:
            futures = {pool.submit(convert, doc): doc for doc in all_docs}
            for done, fut in enumerate(as_completed(futures), start=1):
                warnings.extend(fut.result())          # 有异常在这里抛出,不会被吞
                log(f"   [{done:>2}/{total}] {futures[fut].rel.as_posix()}")
    else:
        for done, doc in enumerate(all_docs, start=1):
            warnings.extend(convert(doc))
            log(f"   [{done:>2}/{total}] {doc.rel.as_posix()}")

    return {name: docs for name, docs in plan}, warnings


# ============================================================== 组装 HTML ==


def render_toc(items: list[tuple[int, str, str]], max_depth: int) -> str:
    """按层级把 (level, text, anchor) 列表渲染成嵌套 <ul>。"""
    pruned = [(lv, tx, an) for lv, tx, an in items if lv <= max_depth]
    if not pruned:
        return ""

    out: list[str] = []
    stack: list[int] = []          # 已打开的层级

    for level, text, anchor in pruned:
        while stack and stack[-1] > level:      # 先关掉比当前更深的层级
            out.append("</li></ul>")
            stack.pop()
        if not stack:
            out.append("<ul>")
            stack.append(level)
        elif stack[-1] == level:                # 同级 → 只结束上一个条目
            out.append("</li>")
        else:                                   # 更深 → 新开一层
            out.append("<ul>")
            stack.append(level)
        out.append(f'<li><a href="#{anchor}">{html.escape(text)}</a>')

    while stack:
        out.append("</li></ul>")
        stack.pop()
    return "\n".join(out)


def group_label(group_name: str) -> str:
    """分组目录名 → 展示名,如 '03-histogram' → '03 · 直方图与对比度'。"""
    label = GROUP_TITLES.get(group_name)
    if label is None:
        label = re.sub(r"^\d+[-_]", "", group_name).replace("-", " ")
    number = re.match(r"^(\d+)", group_name)
    return f"{number.group(1)} · {label}" if number else label


def build_html(
    groups: dict[str, list[Doc]],
    title: str,
    toc_depth: int,
    math: str,
    base_css: str,
) -> tuple[str, list[tuple[int, str, str]]]:
    toc_items: list[tuple[int, str, str]] = []
    body: list[str] = []
    cover_groups: list[str] = []

    for g_index, (group_name, docs) in enumerate(groups.items(), start=1):
        if not docs:
            continue
        display = group_label(group_name)
        anchor = f"group{g_index}"
        cover_groups.append(f"<li>{html.escape(display)}</li>")

        body.append(
            f'<section class="group"><h1 id="{anchor}">{html.escape(display)}</h1>'
            f'<p class="group-sub">{len(docs)} 篇</p></section>'
        )
        toc_items.append((1, display, anchor))

        for doc in docs:
            body.append(f'<section class="doc">')
            body.append(f'<h2 id="{doc.anchor}">{html.escape(doc.title)}</h2>')
            toc_items.append((2, doc.title, doc.anchor))

            # 正文里的 h3~h6 也收进目录页(书签则始终是全量)
            for m in re.finditer(
                r'<h([3-6])\s+id="([^"]+)"[^>]*>(.*?)</h\1>', doc.fragment, re.S
            ):
                plain = html.unescape(re.sub(r"<[^>]+>", "", m.group(3))).strip()
                toc_items.append((int(m.group(1)), plain, m.group(2)))

            body.append(doc.fragment)
            body.append("</section>")

    doc_total = sum(len(d) for d in groups.values())
    group_total = len(cover_groups)

    katex_head = ""
    if math == "katex":
        katex_head = (
            '<link rel="stylesheet" '
            'href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">\n'
            '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>\n'
            '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"\n'
            '  onload="renderMathInElement(document.body,{delimiters:['
            "{left:'\\\\[',right:'\\\\]',display:true},"
            "{left:'\\\\(',right:'\\\\)',display:false}]})\"></script>\n"
        )

    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
{katex_head}<style>
{base_css}
{EXTRA_CSS}
</style>
</head>
<body>
<section class="cover">
  <h1>{html.escape(title)}</h1>
  <p class="cover-sub">按阅读顺序整理 · 共 {doc_total} 篇 / {group_total} 个分组</p>
  <div class="cover-rule"></div>
  <ul class="cover-groups">
{chr(10).join(cover_groups)}
  </ul>
  <p class="cover-foot">生成于 {date.today().isoformat()} · 书签栏即目录,可逐级展开</p>
</section>

<section class="toc">
  <h1 class="toc-title">目录</h1>
  {render_toc(toc_items, toc_depth)}
</section>

<main>
{chr(10).join(body)}
</main>
</body>
</html>
"""
    return page, toc_items


EXTRA_CSS = """
:root { --ink:#1f2328; --muted:#59636e; --line:#d8dee4; --soft:#f6f8fa; }
@page { size: A4; margin: 18mm 16mm 16mm 16mm; }
* { box-sizing: border-box; }
html { font-size: 10.5pt; }
body {
  margin: 0; color: var(--ink); line-height: 1.72;
  font-family: "PingFang SC","Hiragino Sans GB","Heiti SC","Songti SC",
               "Noto Sans CJK SC", system-ui, -apple-system, "Helvetica Neue", sans-serif;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
a { color: #0969da; text-decoration: none; }

/* ---- 封面 ---- */
.cover { height: 240mm; display: flex; flex-direction: column;
         justify-content: center; align-items: center; text-align: center;
         break-after: page; }
.cover h1 { font-size: 30pt; margin: 0 0 6mm; letter-spacing: .04em; line-height: 1.35; }
.cover-sub { color: var(--muted); font-size: 11pt; margin: 0; }
.cover-rule { width: 40mm; height: 2px; background: var(--ink); opacity: .75;
              margin: 10mm 0; }
.cover-groups { list-style: none; padding: 0; margin: 0; color: #3d444d; font-size: 11pt; }
.cover-groups li { margin: 1.6mm 0; }
.cover-foot { color: var(--muted); font-size: 9.5pt; margin-top: 14mm; }

/* ---- 目录页 ---- */
.toc { break-before: page; }
.toc-title { font-size: 20pt; margin: 0 0 6mm; padding-bottom: 3mm;
             border-bottom: 2px solid var(--ink); }
.toc ul { list-style: none; margin: 0; padding-left: 5mm; }
.toc > ul { padding-left: 0; }
.toc li { margin: 1.1mm 0; line-height: 1.5; }
.toc > ul > li { margin-top: 3.2mm; font-weight: 600; font-size: 11pt; }
.toc > ul > li > ul > li { font-weight: 500; }
.toc a { color: var(--ink); }
.toc > ul > li > a { color: #0a3069; }

/* ---- 分组扉页 ---- */
.group { break-before: page; height: 235mm; display: flex; flex-direction: column;
         justify-content: center; align-items: center; text-align: center; }
.group h1 { font-size: 24pt; margin: 0; letter-spacing: .05em; }
.group-sub { color: var(--muted); font-size: 10.5pt; margin-top: 4mm; }

/* ---- 正文 ---- */
.doc { break-before: page; }
.doc > h2 { font-size: 19pt; margin: 0 0 6mm; padding-bottom: 3mm;
            border-bottom: 2px solid var(--line); line-height: 1.4; }
h1, h2, h3, h4, h5, h6 { line-height: 1.4; break-after: avoid; margin: 1.5em 0 .6em; }
h3 { font-size: 14pt; padding-left: 2.5mm; border-left: 3px solid #afb8c1; }
h4 { font-size: 12pt; }
h5, h6 { font-size: 11pt; color: #3d444d; }
p { margin: .7em 0; }
ul, ol { padding-left: 6mm; margin: .7em 0; }
li > ul, li > ol { margin: .3em 0; }
li { margin: .25em 0; }

img { max-width: 100%; height: auto; break-inside: avoid; margin: 1em auto; display: block; }
figure { margin: 1em 0; text-align: center; }
figcaption { color: var(--muted); font-size: 9.5pt; }

pre { background: var(--soft); border: 1px solid var(--line); border-radius: 5px;
      padding: 2.4mm 3mm; margin: .9em 0; font-size: 9pt; line-height: 1.5;
      white-space: pre-wrap; word-break: break-word; break-inside: avoid; }
pre code { background: none; border: none; padding: 0; font-size: inherit; }
pre > code.sourceCode { white-space: pre-wrap; }
code { font-family: "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
       background: var(--soft); border: 1px solid #eaeef2; border-radius: 3px;
       padding: .05em .3em; font-size: .92em; }

table { border-collapse: collapse; width: 100%; margin: .9em 0; font-size: 9.5pt;
        break-inside: avoid; }
th, td { border: 1px solid var(--line); padding: 1.4mm 2mm; vertical-align: top;
         text-align: left; word-break: break-word; }
th { background: var(--soft); font-weight: 600; }

blockquote { margin: .9em 0; padding: .2em 3mm; color: #3d444d;
             border-left: 3px solid #afb8c1; background: #fbfcfd;
             break-inside: avoid; }
blockquote > :first-child { margin-top: .3em; }
blockquote > :last-child { margin-bottom: .3em; }

hr { border: none; border-top: 1px solid var(--line); margin: 1.4em 0; }
strong { font-weight: 600; }

/* 公式(MathML 由 Chrome 原生渲染) */
math { font-size: 1.02em; }
.math.display, math[display="block"] { display: block; text-align: center;
                                       margin: 1em 0; break-inside: avoid; }
"""


# ============================================================== 打印 PDF ===

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
]


def find_chrome(explicit: str | None) -> str:
    if explicit:
        return explicit
    for cand in CHROME_CANDIDATES:
        if "/" in cand:
            if Path(cand).exists():
                return cand
        else:
            found = shutil.which(cand)
            if found:
                return found
    sys.exit("找不到 Chrome/Chromium,可用 --chrome 指定可执行文件路径")


def html_to_pdf(chrome: str, html_path: Path, pdf_path: Path, timeout: float = 300.0) -> None:
    """用 Chrome 打印 PDF。

    坑:headless Chrome 打印完经常不自己退出(实测 PDF 7 秒就写完了,进程却一直挂着),
    所以这里不等进程结束,而是盯着 PDF 文件"写稳"了就收工,再把 Chrome 收掉。
    """
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        pdf_path.unlink()
    # 独立 user-data-dir:避免本机已开着的 Chrome 抢走进程导致什么都不输出
    profile = tempfile.mkdtemp(prefix="docs-pdf-profile-")
    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={profile}",
        "--no-pdf-header-footer",
        "--generate-pdf-document-outline",     # ← 关键:由 h1~h6 生成书签
        "--allow-file-access-from-files",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]

    started = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    settle = 2.0                                   # 文件大小连续稳定 2 秒就认为写完了
    deadline = time.time() + timeout
    last_size, last_change, tick = -1, None, 0
    try:
        while time.time() < deadline:
            time.sleep(0.5)
            size = pdf_path.stat().st_size if pdf_path.exists() else 0
            if size != last_size:
                last_size, last_change = size, time.time()
            elif size > 0 and last_change and time.time() - last_change >= settle:
                break
            if proc.poll() is not None:            # 万一它这次正常退出了
                break
            tick += 1
            if tick % 10 == 0:
                log(f"   打印中 … {last_size / 1024 / 1024:.1f} MB / {time.time() - started:.0f}s")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(profile, ignore_errors=True)

    if not pdf_path.is_file() or pdf_path.stat().st_size < 1024:
        sys.exit(f"Chrome 没能生成 PDF(等待 {time.time() - started:.0f}s)。"
                 f"可用 --chrome 指定可执行文件路径后重试")


def report(pdf_path: Path, toc_items: list[tuple[int, str, str]]) -> None:
    size_mb = pdf_path.stat().st_size / 1024 / 1024
    print(f"\n输出:{pdf_path}  ({size_mb:.1f} MB)")
    try:
        from pypdf import PdfReader
    except ImportError:
        print(f"目录条目:{len(toc_items)} 条(装个 pypdf 可以自检书签)")
        return

    reader = PdfReader(str(pdf_path))
    counted = 0

    def walk(node) -> None:
        nonlocal counted
        for item in node:
            if isinstance(item, list):
                walk(item)
            else:
                counted += 1

    walk(reader.outline)
    print(f"页数:{len(reader.pages)}    书签:{counted} 条")
    if counted == 0:
        print("⚠️ 书签为空,检查 Chrome 是否支持 --generate-pdf-document-outline")


# ============================================================== 增量判断 ==

# 改了这个文件里的样式/模板就 +1,让旧 PDF 判为过期、强制全部重排
STYLE_VERSION = "1"

_MD_IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")


def doc_fingerprint(doc: Doc) -> str:
    """一篇笔记的指纹:正文内容 + 它引用到的图片(用大小/修改时间,不必真读图)。"""
    h = hashlib.sha1()
    try:
        h.update(doc.path.read_bytes())
    except OSError:
        return ""
    base = doc.path.parent
    for m in _MD_IMG_RE.finditer("\n".join(doc.lines)):
        rel = unquote(html.unescape(m.group(1)))
        if rel.startswith(("data:", "http://", "https://")):
            continue
        img = Path(rel if Path(rel).is_absolute() else (base / rel)).resolve()
        try:
            st = img.stat()
        except OSError:
            h.update(b"|missing")
            continue
        h.update(f"|{img}|{st.st_size}|{st.st_mtime_ns}".encode())
    return h.hexdigest()


def build_input_hash(
    groups: dict[str, list[Doc]], args: argparse.Namespace
) -> tuple[str, dict[str, str]]:
    """整本书的输入指纹 + 每篇各自的指纹(后者用来告诉你"哪几篇改了")。"""
    per_doc: dict[str, str] = {}
    h = hashlib.sha1()
    for docs in groups.values():
        for doc in docs:
            key = doc.rel.as_posix()
            fp = doc_fingerprint(doc)
            per_doc[key] = fp
            h.update(key.encode())
            h.update(fp.encode())
    h.update(repr((args.title, args.toc_depth, args.math, EXTRA_CSS, STYLE_VERSION)).encode())
    return h.hexdigest(), per_doc


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_manifest(path: Path, data: dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


# ============================================================== main =======


def main() -> None:
    parser = argparse.ArgumentParser(
        description="把 Documents/ 下的 Markdown 笔记按顺序合并成带书签目录的 PDF",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR, help="笔记根目录")
    parser.add_argument("--out", type=Path, default=None, help="输出 PDF 路径")
    parser.add_argument("--title", default=DEFAULT_TITLE, help="封面标题")
    parser.add_argument("--toc-depth", type=int, default=2,
                        help="目录页展开到第几级(书签始终是全量,不受此限)")
    parser.add_argument("--math", choices=["mathml", "katex", "none"], default="mathml",
                        help="公式渲染方式(mathml 离线,Chrome 原生渲染)")
    parser.add_argument("--exclude", action="append", default=[],
                        help="额外排除的目录名(可重复)")
    parser.add_argument("--keep-html", action="store_true", help="保留中间 HTML")
    parser.add_argument("--list", action="store_true", help="只打印成书顺序")
    parser.add_argument("--open", action="store_true", help="生成后用默认程序打开")
    parser.add_argument("--pandoc", default=None, help="pandoc 可执行文件路径")
    parser.add_argument("--chrome", default=None, help="Chrome 可执行文件路径")
    args = parser.parse_args()

    docs_dir: Path = args.docs_dir.resolve()
    if not docs_dir.is_dir():
        sys.exit(f"目录不存在:{docs_dir}")

    out_pdf = (args.out or docs_dir / "build" / "图像处理学习笔记.pdf").resolve()
    excludes = DEFAULT_EXCLUDE_DIRS | set(args.exclude)

    if args.list:
        groups = collect_only(docs_dir, excludes)
        for group_name, docs in groups.items():
            print(f"\n[{group_name or '(根目录)'}]")
            for d in docs:
                print(f"  {d.index:>2}. {d.rel.as_posix()}   →  {d.title}")
        print(f"\n合计 {sum(len(d) for d in groups.values())} 篇")
        return

    pandoc = find_pandoc(args.pandoc)
    chrome = find_chrome(args.chrome)

    with tempfile.TemporaryDirectory(prefix="docs-book-") as tmp:
        workdir = Path(tmp)
        t0 = time.time()
        log("① 扫描 Markdown 并按阅读顺序转换 …")
        groups, warnings = scan_docs(docs_dir, pandoc, excludes, args.math, workdir)
        doc_total = sum(len(d) for d in groups.values())
        log(f"   {doc_total} 篇,用时 {time.time() - t0:.1f}s")

        log("② 生成目录页并拼装 HTML …")
        page, toc_items = build_html(groups, args.title, args.toc_depth, args.math,
                                     pandoc_highlight_css(pandoc))

        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        html_path = out_pdf.with_suffix(".html") if args.keep_html \
            else workdir / "book.html"
        html_path.write_text(page, encoding="utf-8")
        log(f"   HTML {html_path.stat().st_size / 1024 / 1024:.1f} MB"
            f"{'' if args.keep_html else '(临时)'}")

        log("③ Chrome 打印 PDF 并生成书签 …")
        html_to_pdf(chrome, html_path.resolve(), out_pdf)

        if args.keep_html:
            log(f"   中间 HTML:{html_path}")

    for w in dict.fromkeys(warnings):
        log(f"⚠️ {w}")

    log(f"完成,总用时 {time.time() - t0:.1f}s")
    report(out_pdf, toc_items)

    if args.open:
        subprocess.run(["open", str(out_pdf)], check=False)


def collect_only(docs_dir: Path, excludes: set[str]) -> dict[str, list[Doc]]:
    """--list 用:只做排序和篇名推断,不调用 pandoc。"""
    groups: dict[str, list[Doc]] = {}
    index = 0
    root_mds = sorted((p for p in docs_dir.glob("*.md") if p.is_file()),
                      key=lambda p: sort_key(Path(p.name)))
    if root_mds:
        groups[""] = []
    for path in root_mds:
        index += 1
        doc = Doc(path=path, rel=path.relative_to(docs_dir), index=index, group="")
        doc.headings = scan_headings(path.read_text(encoding="utf-8").splitlines())
        first_h1 = next((h for h in doc.headings if h.level == 1), None)
        doc.title, _ = derive_title(doc, first_h1)
        groups[""].append(doc)

    for entry in sorted(docs_dir.iterdir(), key=lambda p: sort_key(Path(p.name))):
        if not entry.is_dir() or entry.name in excludes or entry.name.startswith("."):
            continue
        mds = sorted((p for p in entry.rglob("*.md") if p.is_file()),
                     key=lambda p: sort_key(p.relative_to(entry)))
        if not mds:
            continue
        groups[entry.name] = []
        for path in mds:
            index += 1
            doc = Doc(path=path, rel=path.relative_to(docs_dir), index=index, group=entry.name)
            doc.headings = scan_headings(path.read_text(encoding="utf-8").splitlines())
            first_h1 = next((h for h in doc.headings if h.level == 1), None)
            doc.title, _ = derive_title(doc, first_h1)
            groups[entry.name].append(doc)
    return groups


if __name__ == "__main__":
    main()
