# Books, cover and title page: design

## Intent

The owner wants a printed-style book that can be split into several volumes, each with a cover
(optionally the owner's own image) and an inside title page. Each volume names its part number.

## Decisions (from the owner)

- Split by **year ranges** the owner types, e.g. `2008-2012,2013-2019,2020-2026`.
- Cover image: **the owner supplies the file**. A typography-only cover is the other option.

## Design

### Books

- `--books 2008-2012,2013-2026` (year ranges, comma-separated, no overlap). Empty = one book with
  the `--from`/`--to` range, as today.
- Each range is one run folder, created in order by the same extract call. Folder names keep the
  existing `book_YYYY-MM-DD_HHMM[_N]` pattern, so the menu's newest-first sort still works.
- A run's `params.json` gains `"part": N, "of": M, "years": [from, to]` (only when split).
- Title: `Facebook 2008–2012`. With more than one book the cover and title page also show `Part N`.

### Cover and title page

- `--cover none|text|image` (default `none`). `image` needs `--cover-image FILE`.
- `--title-page` adds an inside title page (title, `Part N` when split, author from metadata.yaml).
  It can be used with or without a cover.
- Both are written as one Markdown file, `markdown/00-cover.md`, containing a Typst raw block.
  Pandoc sorts it before the years, so it's first in the book. The Typst raw block is only written
  to the Typst output, so the ePub and LaTeX ignore it.
- The cover image is copied into `images/cover.<ext>` (`.avif`/`.heic` are converted to `.jpg`, using
  the same code path as photos).
- ePub: when a cover image is set, `build` passes `--epub-cover-image` (read from `params.json`).
  A text-only cover is not shown in the ePub. This is a known limit.
- Notes stay out of every format. The cover text and title page never contain notes.

### CLI and menu

- `extract` gets `--books`, `--cover`, `--cover-image`, `--title-page`.
- The menu asks for books (Enter = one book), cover (none/text/image, then the path) and title page,
  with defaults from the newest `params.json`.

## Interfaces

- `export.parse_years(value: str) -> list[tuple[int, int]]` raises `ValueError` on bad or overlapping ranges.
- `markdown.write_run(posts, notes, export_root, out_root, params, *, title, cover=None, cover_image=None, title_page=False) -> Path`
  - `cover` is `"text"` or `None`; `cover_image` is a path to the owner's file.
- `build.build(run_dir)` reads `params.json` for `cover_image` to add `--epub-cover-image`.

## Left to the builder

- Cover typography (sizes, colours, layout). Keep it plain.
- Exact Slovak wording for the title page. Use the title and `Part N` only; no imprint text.
