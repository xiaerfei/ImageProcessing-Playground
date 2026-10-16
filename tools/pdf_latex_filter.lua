-- pandoc Lua 过滤器(build_docs_pdf.py --engine latex 用)
--
-- 「怎么读这篇」那张三档表写在引用块里。mdframed 的可断页引用块装不下长表格(longtable),
-- 碰上要跨页的位置会陷进排版死循环(实测 xelatex 吃满 CPU 不返回)。
-- 所以:引用块里有表格 → 换成「不可断页」的版本(整块被推到下一页),其余引用块照旧可断页。

local function has_table(blocks)
  local found = false
  pandoc.walk_block(pandoc.Div(blocks), { Table = function() found = true end })
  return found
end

function BlockQuote(el)
  if has_table(el.content) then
    local out = { pandoc.RawBlock('latex', '\\begin{tablequote}') }
    for _, b in ipairs(el.content) do out[#out + 1] = b end
    out[#out + 1] = pandoc.RawBlock('latex', '\\end{tablequote}')
    return out
  end
end

-- 分隔线:pandoc 默认是居中的半宽黑线,改成通栏浅灰细线(和 Chrome 通道的样式一致)
function HorizontalRule()
  return pandoc.RawBlock('latex',
    '\\par\\vspace{3pt}\\noindent{\\color{ruleline}\\rule{\\linewidth}{0.5pt}}\\par\\vspace{3pt}')
end
