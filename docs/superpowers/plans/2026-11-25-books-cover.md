# Books, cover and title page: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** split the book by owner-chosen year ranges, add an optional cover (text or owner's image) and title page, and show `Part N`.

**Architecture:** the extract step loops over year ranges, one run folder each. A cover/title-page Markdown file with a Typst raw block is written into each run; the Typst build includes it, and the ePub gets the owner's cover image when one is set.

**Tech Stack:** Python 3.15 stdlib, pandoc, typst (unchanged).

**Spec:** docs/superpowers/specs/2026-11-25-books-cover-design.md

## Global Constraints

- Stdlib only. `python -m unittest` must pass after every task.
- Notes never reach the PDF, ePub or print output (the cover and title page included).
- Never print or commit post text, names or images from the export or `output/`.
- Commit trailers: `Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_016tjmpfix7vv5PBfMrCANqe`.

## Review Focus

- `--books` with overlapping ranges, reversed ranges (`2013-2008`), or a bad year → clear error, exit 1.
- `--cover image` without `--cover-image`, or a missing file → clear error, exit 1.
- `--cover-image` with an `.avif` file → converted and used as the ePub cover.

---

### Task 1: Year ranges and multi-part extract

**Files:** Modify `face2book/export.py`, `face2book/__main__.py`, `face2book/markdown.py`; Test `tests/test_export.py`, `tests/test_cli.py`.

**Interfaces:**
- Produces: `parse_years(value: str) -> list[tuple[int, int]]` in export.py.
- Consumes: existing `load(export_root, tz, include, year_from, year_to)`.

- [ ] Write tests: `parse_years("2008-2012,2013-2026") == [(2008, 2012), (2013, 2026)]`; overlap, reversed range and non-year input raise `ValueError`.
- [ ] Implement `parse_years`. Add `--books` (argparse type calls `parse_years`, error exits 1).
- [ ] In `main`, when `--books` is given: for each range call `load(..., year_from=a, year_to=b)`, skip empty parts with a printed line, `write_run` each one with `params` including `part`, `of`, `years`. Print each run folder. Keep the no-`--books` path unchanged.
- [ ] Test (CLI, with the synthetic fixture): two ranges produce two `book_*` folders whose `params.json` has `part` 1 and 2.
- [ ] Run `python -m unittest`. Commit.

### Task 2: Cover, title page, cover image

**Files:** Modify `face2book/markdown.py`, `face2book/build.py`, `face2book/__main__.py`; Test `tests/test_markdown.py`, `tests/test_build.py`.

**Interfaces:**
- Consumes: `copy_image` (markdown.py) for the cover image; `params.json`.
- Produces: `write_run(..., *, title, cover=None, cover_image=None, title_page=False)`; `markdown/00-cover.md`; `images/cover.<ext>`.

- [ ] Tests: with `cover="text"`, `markdown/00-cover.md` exists and contains a `{=typst}` block with the title; with `title_page=True` it contains a second page with the title and `Part N` when given; with `cover_image` a `.png` the file `images/cover.png` exists and the markdown references it.
- [ ] Implement the Typst raw page(s): `#page(margin: 0pt, numbering: none, header: none, footer: none)[...]`. Text is escaped for Typst (`#`, `[`, `]`, `\`, `$`, `*`, `_`).
- [ ] Build: if `params.json` has `cover_image`, add `--epub-cover-image=<images/cover.ext>` to the epub call. Test: the epub contains a cover image entry when a cover image is set.
- [ ] `__main__`: `--cover {none,text,image}` (default none), `--cover-image`, `--title-page`. `image` without a file → error, exit 1. Pass `title` = `Facebook 2008–2012` with ` · Part N` when split.
- [ ] Run tests, confirm no note text in the new cover or title page (add the secret strings to the existing leak test). Commit.

### Task 3: Menu, README, mise

**Files:** Modify `face2book/menu.py`, `README.md`; Test `tests/test_cli.py`.

- [ ] Menu: ask Books (year ranges, Enter = one book, default from `params.json` `years`), Cover (none/text/image; for image ask for the path), Title page (y/n). Defaults from the newest run.
- [ ] Test the menu with a scripted `ask` (existing `menu(out_root, ask=...)` pattern): the returned argv contains `--books`, `--cover`, `--cover-image`, `--title-page` as chosen.
- [ ] README: options, Part naming, the ePub text-cover limit. `mise run` tasks unchanged.
- [ ] Run tests. Commit.
