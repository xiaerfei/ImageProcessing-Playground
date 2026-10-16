#!/usr/bin/env python3
"""检查「生成 PDF 合集」需要的东西装齐了没有;缺什么,直接打印怎么装。

换新电脑时先跑它:

    python3 tools/check_pdf_env.py

它只检查、不安装。三类依赖:
  - chrome 引擎(默认):pandoc + Google Chrome
  - latex 引擎(--engine latex):pandoc + xelatex + 一批 LaTeX 宏包 + 几款 macOS 字体
  - 可选:pypdf(生成后自检书签条数、最长书签字数)
全部满足 → 退出码 0;缺必需项 → 退出码 1。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_docs_pdf import CHROME_CANDIDATES, LATEX_PACKAGES, TEXBIN  # noqa: E402

# 版式里用到的字体 → 用来干什么(都是 macOS 自带;换系统要改 tools/pdf_latex_header.tex)
FONTS = {
    "Songti SC": "正文(宋体-简)",
    "Kaiti SC": "斜体(楷体-简)",
    "PingFang SC": "标题(苹方)",
    "Helvetica Neue": "标题里的西文",
    "STIX Two Text": "正文里的西文、希腊字母",
    "STIX Two Math": "箭头、数学运算符的字形",
    "Menlo": "代码",
    "Apple Symbols": "⚠ 之类的符号",
    "Zapf Dingbats": "✓ ✗",
}

OK, BAD, OPT = "✓", "✗", "·"
missing_required: list[str] = []


def line(mark: str, name: str, note: str = "") -> None:
    print(f"  {mark} {name:<22} {note}")


def check_pandoc() -> None:
    exe = shutil.which("pandoc")
    if not exe:
        line(BAD, "pandoc", "没装 →  brew install pandoc")
        missing_required.append("pandoc")
        return
    out = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout.split("\n")[0]
    ver = re.search(r"(\d+)\.(\d+)", out)
    old = bool(ver) and int(ver.group(1)) < 3
    line(BAD if old else OK, "pandoc", out + ("  ← 太旧,需要 3.x:brew upgrade pandoc" if old else ""))
    if old:
        missing_required.append("pandoc>=3")


def check_chrome() -> None:
    for cand in CHROME_CANDIDATES:
        found = Path(cand).exists() if "/" in cand else shutil.which(cand)
        if found:
            line(OK, "Google Chrome", cand)
            return
    line(BAD, "Google Chrome", "没找到(chrome 引擎需要;只用 latex 引擎可忽略) →  brew install --cask google-chrome")


def texenv() -> dict[str, str]:
    path = os.environ.get("PATH", "")
    if not shutil.which("xelatex", path=path) and Path(TEXBIN, "xelatex").exists():
        path = f"{TEXBIN}:{path}"
    return {**os.environ, "PATH": path}


def check_latex() -> None:
    env = texenv()
    if not shutil.which("xelatex", path=env["PATH"]):
        line(BAD, "xelatex", "没装 →  brew install --cask basictex   (装完重开终端)")
        missing_required.append("xelatex")
        return
    ver = subprocess.run(["xelatex", "--version"], capture_output=True, text=True, env=env).stdout.split("\n")[0]
    in_path = bool(shutil.which("xelatex"))
    line(OK, "xelatex", ver + ("" if in_path else f"   (不在 PATH,脚本会自动用 {TEXBIN})"))

    missing: dict[str, str] = {}
    for fname, pkg in LATEX_PACKAGES.items():
        r = subprocess.run(["kpsewhich", fname], capture_output=True, text=True, env=env)
        if not r.stdout.strip():
            missing[pkg] = fname
    if missing:
        pkgs = " ".join(sorted(missing))
        line(BAD, "LaTeX 宏包", f"缺 {len(missing)} 个:{'、'.join(sorted(missing))}")
        print(f"      sudo tlmgr install {pkgs}")
        print(f"      (不想用 sudo:tlmgr --usermode init-usertree && tlmgr --usermode install {pkgs})")
        missing_required.append("latex 宏包")
    else:
        line(OK, "LaTeX 宏包", f"{len(LATEX_PACKAGES)} 个都在")


def check_fonts() -> None:
    if not shutil.which("fc-list"):
        line(OPT, "字体", "没有 fc-list,跳过检查(非 macOS 请自行改 pdf_latex_header.tex 里的字体名)")
        return
    out = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    have = {name.strip() for ln in out.splitlines() for name in ln.split(",")}
    gone = [f for f in FONTS if f not in have]
    if gone:
        line(BAD, "字体", "缺:" + "、".join(f"{f}({FONTS[f]})" for f in gone))
        print("      都是 macOS 自带字体;非 macOS 请改 tools/pdf_latex_header.tex 里的 \\setCJK... / \\newfontfamily")
        missing_required.append("字体")
    else:
        line(OK, "字体", f"{len(FONTS)} 款都在")


def check_pypdf() -> None:
    try:
        import pypdf  # noqa: F401
        line(OK, "pypdf", "可以自检书签")
    except ImportError:
        line(OPT, "pypdf(可选)", "没装:生成后不会报书签条数/最长书签。装法见 Python-Prototyping/README.md 的 venv")


def main() -> None:
    print("通用")
    check_pandoc()
    print("\nchrome 引擎(默认)")
    check_chrome()
    print("\nlatex 引擎(--engine latex)")
    check_latex()
    check_fonts()
    print("\n可选")
    check_pypdf()
    print()
    if missing_required:
        print("还缺:" + "、".join(missing_required) + "。按上面的提示装完,再跑一次本脚本。")
        sys.exit(1)
    print("齐了。生成:python3 tools/build_docs_pdf.py   或   python3 tools/build_docs_pdf.py --engine latex")


if __name__ == "__main__":
    main()
