#!/usr/bin/env python3
"""把本目录的 .tex 笔记编译成 PDF，编译完删掉中间文件。

用法（在任意目录执行都行）：
    python3 build_pdf.py              编译本目录全部 .tex
    python3 build_pdf.py 03 04        只编译文件名里含 03 或 04 的
    python3 build_pdf.py --check      只检查环境（xelatex、宏包、字体），不编译
    python3 build_pdf.py --install    用 tlmgr 补装缺的宏包（会要 sudo 密码）
    python3 build_pdf.py --keep       编译后保留中间文件（.aux/.log 等）

换一台 Mac 编不过，几乎都是下面三种原因之一，脚本会先查一遍再编：
  1. 没装 TeX：装 BasicTeX（brew install --cask basictex）或 MacTeX；
  2. 缺宏包：BasicTeX 只带最基本的包，笔记用到的 ctex、mdframed、tikz 等要另装，
     跑 `python3 build_pdf.py --install` 一次装齐；
  3. 缺字体：「宋体-简 Songti SC」在新版 macOS 上默认不下载，
     打开「字体册」搜「宋体-简」点「下载」。

只用 Python 标准库，兼容 macOS 自带的 Python 3.9。
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))

# 笔记用到、但 BasicTeX（scheme-basic）不带的 TeX Live 包。
# 每项是（kpsewhich 能找到的代表文件, tlmgr 包名）。清单由 xelatex -recorder 记录的实际读取文件反推而来。
REQUIRED = [
    ("ctexart.cls", "ctex"),
    ("xeCJK.sty", "xecjk"),
    ("fontspec.sty", "fontspec"),
    ("zhnumber.sty", "zhnumber"),
    ("CJKfntef.sty", "cjk"),
    ("tikz.sty", "pgf"),
    ("mdframed.sty", "mdframed"),
    ("zref-abspage.sty", "zref"),
    ("needspace.sty", "needspace"),
    ("enumitem.sty", "enumitem"),
    ("booktabs.sty", "booktabs"),
    ("float.sty", "float"),
    ("xcolor.sty", "xcolor"),
]

# 编译产生的中间文件后缀，清理时只删这些。
JUNK_EXTS = (".aux", ".log", ".out", ".toc", ".synctex.gz", ".fls", ".fdb_latexmk",
             ".xdv", ".bbl", ".blg", ".lof", ".lot", ".nav", ".snm", ".bcf", ".run.xml")

# Finder / VS Code 启动的进程可能没继承 PATH，所以除了 PATH 再试几个常见安装位置。
TEX_DIRS = ["/Library/TeX/texbin", "/usr/local/texlive/2026/bin/universal-darwin",
            "/usr/local/texlive/2026basic/bin/universal-darwin", "/opt/homebrew/bin", "/usr/local/bin"]


def say(msg=""):
    print(msg, flush=True)


def find_tool(name):
    path = shutil.which(name)
    if path:
        return path
    for d in TEX_DIRS:
        cand = os.path.join(d, name)
        if os.access(cand, os.X_OK):
            return cand
    return None


def tex_files(patterns):
    files = sorted(f for f in os.listdir(HERE) if f.endswith(".tex"))
    if patterns:
        files = [f for f in files if any(p in f for p in patterns)]
    return files


def missing_packages(kpsewhich):
    """返回缺的 tlmgr 包名列表。"""
    names = [f for f, _ in REQUIRED]
    out = subprocess.run([kpsewhich] + names, capture_output=True, text=True).stdout
    found = {os.path.basename(line.strip()) for line in out.splitlines() if line.strip()}
    return [pkg for f, pkg in REQUIRED if f not in found]


def installed_font_families():
    """用 macOS 的 NSFontManager 列出已安装（已下载）的字体族名；拿不到时返回 None。"""
    js = ('ObjC.import("AppKit");'
          'ObjC.deepUnwrap($.NSFontManager.sharedFontManager.availableFontFamilies).join("\\n")')
    try:
        out = subprocess.run(["osascript", "-l", "JavaScript", "-e", js],
                             capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    fams = {line.strip() for line in out.splitlines() if line.strip()}
    return fams or None


def fonts_needed(files):
    """从 .tex 里读出 \\setCJKmainfont / \\setCJKsansfont / \\setmainfont 等用到的字体族。"""
    fams = set()
    pat = re.compile(r"\\set(?:CJK)?(?:main|sans|mono)font\{([^}]+)\}")
    for f in files:
        with open(os.path.join(HERE, f), encoding="utf-8") as fh:
            fams.update(m.strip() for m in pat.findall(fh.read()))
    return sorted(fams)


def check_env(files, verbose=True):
    """检查 xelatex、宏包、字体。返回 (xelatex 路径或 None, 缺的包, 缺的字体)。"""
    xelatex = find_tool("xelatex")
    kpsewhich = find_tool("kpsewhich")
    if not xelatex or not kpsewhich:
        say("✗ 没找到 xelatex。先装 TeX：")
        say("    brew install --cask basictex     # 约 100 MB，装完重开终端")
        say("  或到 https://tug.org/mactex/ 下载 MacTeX（完整版，约 6 GB，不用再补宏包）。")
        return None, [], []
    if verbose:
        say("✓ xelatex：" + xelatex)

    miss_pkgs = missing_packages(kpsewhich)
    if miss_pkgs:
        say("✗ 缺 TeX 宏包：" + " ".join(miss_pkgs))
        say("    python3 build_pdf.py --install   # 或手动：sudo tlmgr install " + " ".join(miss_pkgs))
    elif verbose:
        say("✓ 宏包齐全")

    miss_fonts = []
    fams = installed_font_families()
    if fams is None:
        if verbose:
            say("? 查不到系统字体列表，跳过字体检查")
    else:
        miss_fonts = [f for f in fonts_needed(files) if f not in fams]
        if miss_fonts:
            say("✗ 缺字体：" + "、".join(miss_fonts))
            say("    打开「字体册」，搜索字体名（宋体-简 = Songti SC，苹方-简 = PingFang SC），点「下载」。")
        elif verbose:
            say("✓ 字体齐全")
    return xelatex, miss_pkgs, miss_fonts


def install_packages(tlmgr, pkgs):
    say("用 tlmgr 安装：" + " ".join(pkgs) + "（需要输入本机登录密码）")
    # 远端仓库升级过时，tlmgr 会要求先升级自己，否则 install 直接失败，所以先 update --self。
    subprocess.run(["sudo", tlmgr, "update", "--self"])
    rc = subprocess.run(["sudo", tlmgr, "install"] + pkgs).returncode
    return rc == 0


def first_error(log_text):
    """从 .log 里摘出第一处错误和它后面几行。"""
    lines = log_text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("!") or re.match(r"^\./.*:\d+: ", line):
            return "\n".join(lines[i:i + 8])
    return "\n".join(lines[-15:])


def hint_for(err):
    m = re.search(r"File `([^']+)' not found", err)
    if m:
        return ("缺文件 {0}：查它属于哪个包 → tlmgr search --global --file {0}，"
                "再 sudo tlmgr install <包名>".format(m.group(1)))
    m = re.search(r'The font "([^"]+)" cannot be found', err)
    if m:
        return "缺字体 {}：打开「字体册」搜索并下载。".format(m.group(1))
    return ""


def compile_one(xelatex, tex):
    """在临时目录里编译（两遍：第二遍补目录、交叉引用和书签），成功后把 PDF 拷回本目录。"""
    name = tex[:-4]
    start = time.time()
    with tempfile.TemporaryDirectory(prefix="texbuild-") as tmp:
        cmd = [xelatex, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error",
               "-output-directory=" + tmp, tex]
        for _ in range(2):
            proc = subprocess.run(cmd, cwd=HERE, capture_output=True)
            if proc.returncode != 0:
                log_path = os.path.join(tmp, name + ".log")
                log_text = ""
                if os.path.exists(log_path):
                    with open(log_path, encoding="utf-8", errors="replace") as fh:
                        log_text = fh.read()
                    # 失败时把完整日志留在本目录，方便对照；成功编译后会被清理掉。
                    shutil.copy(log_path, os.path.join(HERE, name + ".log"))
                else:
                    log_text = proc.stdout.decode("utf-8", "replace")
                return tex, False, time.time() - start, first_error(log_text)
        shutil.copy(os.path.join(tmp, name + ".pdf"), os.path.join(HERE, name + ".pdf"))
    return tex, True, time.time() - start, ""


def clean(keep_logs_for=()):
    removed = 0
    for f in os.listdir(HERE):
        if f.endswith(JUNK_EXTS):
            if f.endswith(".log") and f[:-4] + ".tex" in keep_logs_for:
                continue
            os.remove(os.path.join(HERE, f))
            removed += 1
    return removed


def main():
    ap = argparse.ArgumentParser(description="编译本目录的 LaTeX 笔记为 PDF")
    ap.add_argument("patterns", nargs="*", help="只编译文件名包含这些字样的 .tex")
    ap.add_argument("--check", action="store_true", help="只检查环境")
    ap.add_argument("--install", action="store_true", help="用 tlmgr 补装缺的宏包")
    ap.add_argument("--keep", action="store_true", help="保留中间文件")
    args = ap.parse_args()

    files = tex_files(args.patterns)
    if not files:
        say("没有匹配的 .tex 文件。")
        return 1

    xelatex, miss_pkgs, miss_fonts = check_env(files, verbose=args.check or args.install)
    if not xelatex:
        return 1
    if args.install:
        if not miss_pkgs:
            say("宏包已齐全，不用装。")
        elif not install_packages(find_tool("tlmgr"), miss_pkgs):
            say("安装失败，看上面 tlmgr 的报错。")
            return 1
        else:
            miss_pkgs = missing_packages(find_tool("kpsewhich"))
            say("✓ 安装完成" if not miss_pkgs else "✗ 仍缺：" + " ".join(miss_pkgs))
        return 0 if not miss_pkgs else 1
    if args.check:
        return 0 if not (miss_pkgs or miss_fonts) else 1
    if miss_pkgs or miss_fonts:
        say("环境不全，先按上面的提示补齐再编译。")
        return 1

    say("编译 {} 个文件……".format(len(files)))
    failed = []
    with ThreadPoolExecutor(max_workers=min(4, len(files))) as pool:
        for tex, ok, secs, err in pool.map(lambda t: compile_one(xelatex, t), files):
            if ok:
                say("  ✓ {}.pdf（{:.1f} 秒）".format(tex[:-4], secs))
            else:
                failed.append(tex)
                say("  ✗ {}（{:.1f} 秒）".format(tex, secs))
                say("    " + err.replace("\n", "\n    "))
                hint = hint_for(err)
                if hint:
                    say("    → " + hint)

    if not args.keep:
        n = clean(keep_logs_for=failed)
        say("已删除 {} 个中间文件。".format(n))
    if failed:
        say("有 {} 个失败，完整日志留在同名 .log 里。".format(len(failed)))
        return 1
    say("全部完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
