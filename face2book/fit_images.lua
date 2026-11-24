-- Typst only. Each post (a `post` div) is one unbreakable block, so its text and photos stay
-- on one page, even if that leaves white space. Photos inside a post share its height:
-- one photo gets up to 60% of the page, two get 30% each, and so on.
-- Other photos get the same size cap. "contain" keeps the whole photo; Typst's default
-- "cover" would crop it.
local function fit(img, share)
  img.attributes.width = "100%"
  img.attributes.height = share
  return img
end

function Image(el)
  if FORMAT ~= "typst" then return el end
  return fit(el, "60%")
end

function Div(el)
  if FORMAT ~= "typst" or not el.classes:includes("post") then return nil end
  local count = 0
  el:walk({ Image = function() count = count + 1 end })
  local share = string.format("%d%%", math.floor(60 / math.max(count, 1)))
  el = el:walk({ Image = function(img) return fit(img, share) end })
  local blocks = { pandoc.RawBlock("typst", "#block(breakable: false)[") }
  for _, b in ipairs(el.content) do blocks[#blocks + 1] = b end
  blocks[#blocks + 1] = pandoc.RawBlock("typst", "]")
  return blocks
end

function Meta(m)
  if FORMAT ~= "typst" then return m end
  local raw = pandoc.RawBlock("typst", '#set image(fit: "contain")')
  m["header-includes"] = pandoc.MetaList({pandoc.MetaBlocks({raw})})
  return m
end
