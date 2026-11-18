# Face2Book

Turns a Facebook "Download Your Information" export (JSON format) into a book:
a Markdown master copy, plus PDF, ePub and print sources (`.typ`, `.tex`).
Python standard library only; pandoc and typst do the conversion.

## Setup

    mise install        # python, pandoc, typst (see mise.toml)

## Use

    python -m face2book                      # guided menu
    python -m face2book extract <export> [--out output] [--tz Europe/Bratislava] \
        [--include timeline,others-timeline,groups,life-events] [--from YEAR] [--to YEAR]
    python -m face2book build <run_dir>      # rebuild book files from markdown/

Each extract creates `output/book_YYYY-MM-DD_HHMM[_N]/`:

    images/            photos referenced by posts
    markdown/<year>.md one file per year, plus metadata.yaml
    params.json        the options used (the menu reuses the newest one)
    book.pdf  book.epub
    print/book.typ  print/book.tex

## Editing

Edit the files in `markdown/`, then run `build <run_dir>` to regenerate every format.
The Markdown is the master copy; the other files are overwritten on each build.

## Notes rule

Comments by other people are kept in the Markdown as `::: note` blocks, so the master
copy is complete. The print sources (`.typ`, `.tex`) are built without them.
PDF and ePub are built without them too.

## What's in the book / what isn't

In (merged by year). No kind is merged into timeline.
- `timeline`: your own posts (text, photos with captions; shared links only when you wrote text — the link itself isn't printed)
- `others-timeline`: your posts on other people's pages (this export has none with content)
- `groups`: your posts in groups
- `life-events`: life events (this export has only their names)

Not in the book:
- friends' comments and friends' posts on your timeline (Facebook no longer exports them,
  so there are no notes)
- your comments on other people's posts
- photos that only appear in albums, videos, Facebook Notes (`notes.json`)
- images Typst cannot read (`.avif`), skipped with a warning

Edit `markdown/metadata.yaml` for the book's title and author.

Layout details: `docs/export-layout.md`.
