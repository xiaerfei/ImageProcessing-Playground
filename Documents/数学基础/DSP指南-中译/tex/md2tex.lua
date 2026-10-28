-- md2tex.lua：把 DSP 指南译稿的 Markdown 转成可被 main.tex \include 的章节文件。
-- 由 build-tex.sh 调用，每个 md 单独跑一次；元数据 fileid 是文件名前缀（如 02、00b、35）。

local fileid = ""
local chaptitle = nil

-- 图片宽度：原书整版宽的图裁出来约 1200 像素，按这个比例缩放，保持原书里大图小图的相对尺寸。
local FULL_WIDTH_PX = 1200

local function latex(inlines)
  return pandoc.write(pandoc.Pandoc({ pandoc.Plain(inlines) }), "latex")
end

local function figure_block(img, caption_inlines)
  local width = 1.0
  local fh = io.open(img.src, "rb")
  if fh then
    local ok, w = pcall(function()
      return pandoc.image.size(fh:read("a")).width
    end)
    fh:close()
    if ok and w then width = math.min(w / FULL_WIDTH_PX, 1.0) end
  end
  local lines = {
    "\\begin{figure}[htbp]",
    "\\centering",
    string.format("\\includegraphics[width=%.3f\\linewidth,height=0.8\\textheight,keepaspectratio]{%s}",
      width, img.src),
  }
  if caption_inlines then
    table.insert(lines, "\\caption*{" .. latex(caption_inlines) .. "}")
  end
  table.insert(lines, "\\end{figure}")
  return pandoc.RawBlock("latex", table.concat(lines, "\n"))
end

local function single_image(blk)
  if (blk.t == "Para" or blk.t == "Plain") and #blk.content == 1 and blk.content[1].t == "Image" then
    return blk.content[1]
  end
end

-- 图片下面紧跟的「**图 X-Y　……**」段落就是图注
local function is_caption(blk)
  if not blk or blk.t ~= "Para" then return false end
  local first = blk.content[1]
  return first and first.t == "Strong" and pandoc.utils.stringify(first):match("^图") ~= nil
end

function Meta(meta)
  fileid = pandoc.utils.stringify(meta.fileid or "")
  if meta.chaptitle then chaptitle = pandoc.utils.stringify(meta.chaptitle) end
end

function RawInline(el)
  if el.format == "html" and el.text:match("^<br%s*/?>$") then
    return pandoc.LineBreak()
  end
end

-- 正文字体 STIX Two Text 里没有的符号，交给 main.tex 的 \dspsym 用数学字体显示
local SYMBOLS = {}
for _, cp in utf8.codes("←→↔⇄∗√∝∞∫≈≤≥⊕⋯⋮□△○⚠") do SYMBOLS[utf8.char(cp)] = true end

function Str(el)
  if not utf8.len(el.text) then return nil end
  local out, buf, hit = pandoc.List(), {}, false
  for _, cp in utf8.codes(el.text) do
    local ch = utf8.char(cp)
    local repl
    if ch == "ₙ" then
      repl = pandoc.Subscript({ pandoc.Str("n") })
    elseif SYMBOLS[ch] then
      repl = pandoc.RawInline("latex", "\\dspsym{" .. ch .. "}")
    end
    if repl then
      if #buf > 0 then out:insert(pandoc.Str(table.concat(buf))); buf = {} end
      out:insert(repl)
      hit = true
    else
      table.insert(buf, ch)
    end
  end
  if not hit then return nil end
  if #buf > 0 then out:insert(pandoc.Str(table.concat(buf))) end
  return out
end

-- <sub>x</sub> → 下标
function Inlines(inls)
  local out, i = pandoc.List(), 1
  while i <= #inls do
    local el = inls[i]
    if el.t == "RawInline" and el.format == "html" and el.text == "<sub>" then
      local j, inner = i + 1, pandoc.List()
      while j <= #inls and not (inls[j].t == "RawInline" and inls[j].text == "</sub>") do
        inner:insert(inls[j]); j = j + 1
      end
      out:insert(pandoc.Subscript(inner))
      i = j + 1
    else
      out:insert(el); i = i + 1
    end
  end
  return out
end

-- 列多的数值表（如第 20 章的切比雪夫系数表）按正常字号会冲出版心，缩小字号和列间距
function Table(el)
  local ncol = #el.colspecs
  if ncol < 6 then return nil end
  local size = ncol >= 8 and "\\scriptsize" or "\\footnotesize"
  return {
    pandoc.RawBlock("latex", "\\begingroup" .. size .. "\\setlength{\\tabcolsep}{3pt}"),
    el,
    pandoc.RawBlock("latex", "\\endgroup"),
  }
end

-- 指向其他章节 md 的链接改成 PDF 内跳转
function Link(el)
  local id = el.target:match("^(%d%d%a?)%-DSP[^#]*%.md")
  if id then
    if id == "00a" then return el.content end -- 目录页由 \tableofcontents 生成，不再单独收录
    el.target = "#ch-" .. id
    return el
  end
end

function Pandoc(doc)
  local blocks = doc.blocks
  -- 去掉文件头：书名 H1、说明引用块和分隔线，这些是给 md 读者看的
  local start = 1
  for i, b in ipairs(blocks) do
    if b.t == "HorizontalRule" then start = i + 1; break end
  end

  local out = pandoc.List()
  local labelled = false
  local i = start
  while i <= #blocks do
    local b = blocks[i]
    local img = single_image(b)
    if img then
      if is_caption(blocks[i + 1]) then
        out:insert(figure_block(img, blocks[i + 1].content)); i = i + 2
      else
        out:insert(figure_block(img, nil)); i = i + 1
      end
    elseif b.t == "Header" and b.level == 1 and not labelled then
      -- 「第 2 章　标题」→ \chapter{标题}，章号交给 LaTeX 编
      local title = pandoc.utils.stringify(b.content):gsub("^第%s*%d+%s*章[%s　]*", "")
      out:insert(pandoc.Header(1, pandoc.Inlines(title), pandoc.Attr("ch-" .. fileid)))
      labelled = true; i = i + 1
    else
      out:insert(b); i = i + 1
    end
  end

  if not labelled and chaptitle then
    out:insert(1, pandoc.Header(1, pandoc.Inlines(chaptitle), pandoc.Attr("ch-" .. fileid)))
  end
  return pandoc.Pandoc(out, doc.meta)
end

return {
  { Meta = Meta },
  { RawInline = RawInline, Inlines = Inlines, Link = Link, Str = Str, Table = Table },
  { Pandoc = Pandoc },
}
