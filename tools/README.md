# tools

仓库的维护工具:把笔记排成 PDF、检查文档链接。

| 文件 | 干什么 |
| :--- | :--- |
| [`build_docs_pdf.py`](build_docs_pdf.py) | 把 `Documents/` 下的笔记排成带书签的 PDF,一个主题一本 |
| [`check_pdf_env.py`](check_pdf_env.py) | 环境体检:检查下面这些东西装齐没有,缺什么直接打印安装命令 |
| [`check_doc_links.py`](check_doc_links.py) | 检查笔记里的链接、锚点有没有断 |
| [`pdf_latex_header.tex`](pdf_latex_header.tex)、[`pdf_latex_filter.lua`](pdf_latex_filter.lua) | xelatex 引擎的版式与过滤器 |

## 需要安装什么(macOS)

| 要装的 | 用来干什么 | 哪个引擎要 |
| :--- | :--- | :--- |
| pandoc(3.x) | Markdown 转 HTML / LaTeX | 两个都要 |
| Google Chrome | 把 HTML 打印成 PDF | Chrome 引擎(默认) |
| BasicTeX | xelatex 排版 | xelatex 引擎(`--engine latex`) |
| 12 个 LaTeX 宏包 | 中文、标题、引用块、代码折行、表格等 | xelatex 引擎 |
| 9 款 macOS 自带字体 | 宋体-简、楷体-简、苹方、Helvetica Neue、STIX Two Text、STIX Two Math、Menlo、Apple Symbols、Zapf Dingbats | xelatex 引擎(系统自带,不用装) |
| Python 3 | 跑构建脚本(系统自带 3.9 就行,无第三方依赖) | 两个都要 |
| Python venv + `requirements.txt` | 跑 `Python-Prototyping/` 的脚本、出图;含 `pypdf`(自检书签) | 可选 |

安装命令:

```bash
brew install pandoc
```

```bash
brew install --cask google-chrome
```

```bash
brew install --cask basictex
```

BasicTeX 装完重开终端,再补 12 个宏包:

```bash
sudo tlmgr install ctex xecjk fontspec enumitem framed fvextra mdframed multirow needspace newunicodechar titlesec xurl zref
```

没有 sudo 权限:先 `tlmgr --usermode init-usertree`,再把 `sudo tlmgr` 换成 `tlmgr --usermode`。

Python venv(可选,详见 [`Python-Prototyping/README.md`](../Python-Prototyping/README.md)):

```bash
python3 -m venv Python-Prototyping/.venv
```

```bash
Python-Prototyping/.venv/bin/pip install -r Python-Prototyping/requirements.txt
```

## 装完体检,然后生成

```bash
python3 tools/check_pdf_env.py
```

```bash
python3 tools/build_docs_pdf.py
```

```bash
python3 tools/build_docs_pdf.py --engine latex
```

输出在 `Documents/build/`。常用选项:`--only 复变函数`(只出一本)、`--merge`(合成一份)、`--list`(只列成书顺序)。
宏包清单以体检脚本为准(上面的命令是写这份文档时的快照)。
