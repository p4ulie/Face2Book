# Face2Book rewrite: design

## Intent

Turn the owner's Facebook "Download Your Information" export into a personal book. The Markdown is
the master copy: the owner reviews and hand-edits it, then builds the finished formats from it. It is
tested on the owner's own account.

The prototype (`face2book.py`, `run_all.sh`) prints one HTML page per year from a 2018-era export.
This rewrite replaces it.

## Goals

- Read a current Facebook JSON export and write one run folder per run, named with date and time
  (`book_2026-11-18_1430/`) so runs can be compared side by side.
- The run folder holds `images/`, `markdown/`, `book.pdf`, `book.epub`, and `print/` (`book.typ` + `book.tex`).
- The book content is the owner's own posts and the photos attached to them.
- Notes (friends' comments, friends' posts on the owner's timeline) appear only in the Markdown, next
  to the post or day they belong to. They never reach PDF, ePub or print.
- After the owner edits the Markdown, the finished formats can be rebuilt without re-reading the export.
- Small, readable modules, each with one job.

## Non-goals

- Messenger conversations.
- Fetching from Facebook live (Graph API, scraping). Input is the offline export only.
- Supporting the 2018 export layout the prototype reads. Only the current layout is supported.
- Reactions/likes, check-ins as their own entries, albums uploaded without a post.

## Anti-goals

- A friend's words appearing in PDF, ePub or print output. That counts as failure even if everything
  else works.
- Broken Slovak characters (mojibake) anywhere in the output.

## Constraints

- Facebook writes UTF-8 bytes as `\u00XX` escapes. Every string needs `s.encode('latin-1').decode('utf-8')`
  after `json.load`.
- Post titles are in the account's language. The owner's Facebook may be Slovak. Filtering must not
  depend on English title text.
- Image paths in the export are relative to the export root.
- The Python side uses only the standard library (`json`, `zoneinfo`, `pathlib`, `argparse`, `shutil`,
  `subprocess`, `dataclasses`). Python 3.12+.
- External tools: `pandoc` (3.1+, for Typst support) and `typst`, pinned in the project's `mise.toml`
  (`pandoc = "3.8"`, `typst = "0.14"`, or the latest available). Install them with `mise install`, which
  needs no sudo, so the implementer can do it. LaTeX is not needed: pandoc writes `.tex` source without it.
- Friends' comments on plain text posts may not be in the export at all. The prototype only found
  comments on photo attachments (`media.comments`). Notes contain whatever the export actually has.

## Approaches considered

- **A. Pandoc + Typst (picked).** Pandoc writes the ePub, and the PDF via Typst. A Lua filter drops
  notes. Print source: `.typ` and `.tex`, both from pandoc. Least code, every format the owner asked
  for, small install.
- **B. Pandoc + LaTeX.** Same as A, but with a 2–5 GB install and slower, harder-to-debug builds. A
  already produces `.tex` for a print shop.
- **C. Pure Python (WeasyPrint + ebooklib).** Most code, no real print source, new dependencies.

The owner picked A.

## Design

### Package layout

```
face2book/
  __main__.py     CLI: `python -m face2book extract …` / `build …`
  export.py       read the export → list[Post]; mojibake fix; finds the JSON files
  markdown.py     list[Post] → run folder: markdown/<year>.md, metadata.yaml, images/
  build.py        markdown/ → book.epub, book.pdf, print/book.typ, print/book.tex (calls pandoc)
  drop_notes.lua  pandoc filter that removes every `::: note` div
tests/
  test_face2book.py
```

The prototype files are deleted. Git history keeps them.

### Data model (`export.py`)

```python
@dataclass
class Post:
    when: datetime            # timezone-aware, converted to the book's timezone
    text: str                 # the owner's own words; "" if none
    images: list[Path]        # relative to the export root
    kind: str                 # timeline | others-timeline | groups | life-events
    notes: list[str]          # "Author: text" lines: every comment, the owner's own replies included

@dataclass
class TimelineNote:           # a friend's post on the owner's timeline
    when: datetime
    author: str
    text: str
```

`load(export_root, tz) -> tuple[list[Post], list[TimelineNote]]`, sorted by time.

### Which posts are book content

The owner wants to re-run the generator on the same download with different settings and compare the
results. Content selection is therefore a set of CLI flags, and every run records them.

- `--include` takes a comma-separated list of post kinds. The default is everything: `timeline` (own
  timeline), `others-timeline` (owner's posts on friends' timelines), `groups`, `life-events`.
  The kinds are told apart by export structure (which file a post is in, or which keys it has), not by
  title text. The builder maps each kind to real structure after inspecting the export. Any kind the
  export can't distinguish is merged into `timeline`, and the README says so.
- `--from YEAR` / `--to YEAR` limit the date range. This replaces `run_all.sh`.
- Every run writes `params.json` into its run folder, holding the full command-line settings and the
  export path, so two runs can be compared.

Within the selected kinds, a post is kept if it has text the owner wrote, or images. A share with no text of the owner's own
(link, post, video) is dropped. The decision uses structure (`data[].post` present and non-empty,
`attachments[].data[].media` present), not the title text, so it works in any account language.
Empty `data` entries never print as "None".

Videos: the video file is dropped. The post is kept if it has the owner's text or a photo, and a
video-only post is dropped. *(Builder's call: a later version could use the video thumbnail.)*

### Markdown (`markdown.py`)

- One file per year: `markdown/2009.md`. Inside it: `# 2009`, then `## <month>` and `### <date>` headings,
  with each post shown as its time in italics followed by its text.
- Images: `![](../images/<name>)`. Only images used by kept posts are copied from the export into `images/`.
- All comments, the owner's own replies included, are notes. The owner's comments on other people's
  posts are left out entirely.
- Notes go in a fenced div right after their post:

  ```markdown
  ::: note
  **Jana:** Congrats!!
  :::
  ```

  A friend's timeline post goes into a `::: note` under the matching day heading. If a day, month or
  year holds only notes, its heading goes *inside* the note div. The filter then removes the heading
  together with the notes, and the book shows no empty dates. *(Builder's call.)*
- Owner text is Markdown-escaped, so `*`, `#`, `<` and similar characters in posts can't break formatting.
- `markdown/metadata.yaml` holds `title`, `author`, `lang: sk` and is written once. The owner can edit it.
- Month names and date format are Slovak (`marec 2009`, `14. 3. 2009`), from a hard-coded list rather
  than the system locale. *(Builder's call: confirm with the owner if in doubt.)*

### Build (`build.py`)

Runs pandoc on `metadata.yaml` + `markdown/*.md` in year order, with
`--lua-filter drop_notes.lua --resource-path markdown`:

- `book.epub`
- `book.pdf` via `--pdf-engine=typst`
- `print/book.typ` and `print/book.tex` (pandoc `-t typst`, `-t latex -s`)

All four outputs go through the filter. If pandoc or typst is missing, the build fails with a clear
message naming `mise install`. The implementer runs `mise install` before the build tasks. The
anti-goal test **fails** (it doesn't skip) when pandoc is missing.

### CLI

```
python -m face2book extract <export_dir> [--out output/] [--tz Europe/Bratislava]
                             [--include timeline,others-timeline,groups,life-events]
                             [--from YEAR] [--to YEAR]
    → creates output/book_<YYYY-MM-DD_HHMM>/ with markdown/ + images/, then builds
python -m face2book build <run_dir>
    → rebuilds the finished formats from that run folder's (possibly edited) Markdown
```

`output/` is git-ignored: it holds personal data.

### Tests

There is one file, `tests/test_face2book.py`. It runs with `python -m unittest` and uses a tiny export
built in a temp dir. It covers:

- The mojibake fix (`"Ä\u008d"` style input → `č`).
- Share-only posts are dropped. A share with the owner's text is kept. Nothing prints `None`.
- Notes land inside `::: note` blocks, and the owner's text is escaped.
- `--include` and `--from`/`--to` filter as expected, and `params.json` is written.
- Build the fixture, then check that no note text appears in `print/book.typ`
  or the ePub. This is the anti-goal check.

## Input

The owner requests a JSON export (full date range, with posts, comments and photos included) and gives
its path. Plan task 1 blocks until that path exists. The builder may read the export.

## Left to the builder

- The exact JSON file names and keys in the current export. Inspect the owner's real export first
  (task 1 of the plan), and code against what is actually there.
- Where friends' timeline posts and comments live in the export, or whether they're missing.
- Book typography (fonts, margins, image width). Pandoc's Typst defaults are fine for v1.
