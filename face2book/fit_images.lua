-- Typst only: scale each photo to the text width and at most 60% of the page height,
-- so a tall photo doesn't get pushed to a new page and leave the previous page half empty.
-- "contain" keeps the whole photo; Typst's default "cover" would crop it.
function Image(el)
  if FORMAT ~= "typst" then return el end
  el.attributes.width = "100%"
  el.attributes.height = "60%"
  return el
end

function Meta(m)
  if FORMAT ~= "typst" then return m end
  local raw = pandoc.RawBlock("typst", '#set image(fit: "contain")')
  m["header-includes"] = pandoc.MetaList({pandoc.MetaBlocks({raw})})
  return m
end
