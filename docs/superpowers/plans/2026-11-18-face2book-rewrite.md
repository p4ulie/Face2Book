# Face2Book Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a Facebook JSON export into a timestamped run folder with editable Markdown (friends' words only in `::: note` blocks) plus PDF, ePub and print source built without the notes.

**Architecture:** A stdlib-only Python package: `export.py` reads the JSON into `Post`/`TimelineNote` objects, `markdown.py` writes the run folder, `build.py` calls pandoc (with a Lua filter that drops notes) for ePub, PDF via Typst, `.typ` and `.tex`. `__main__.py` is the CLI, and `menu.py` is a guided prompt that returns CLI arguments.

**Tech Stack:** Python 3.15 (stdlib only, `unittest`), pandoc 3, typst, all pinned in `mise.toml`.

**Spec:** `docs/superpowers/specs/2026-11-18-face2book-rewrite-design.md`

**Task order:** Tasks 1–4 don't need the owner's export: they test with `Post` objects built in code. Task 5 waits until the owner gives the export path.

## Global Constraints

- Python side uses only the standard library. No pip installs.
- `pandoc` and `typst` come from `mise.toml`, installed with `mise install` (no sudo).
- Friends' words (all comments, the owner's own replies included, and friends' timeline posts) appear only inside `::: note` divs. They never reach `book.pdf`, `book.epub`, `print/book.typ` or `print/book.tex`.
- Strings from the export pass through `fix_text` (`s.encode('latin-1').decode('utf-8')`).
- Book content is never filtered by title text (the account may be in Slovak).
- Slovak dates are hard-coded, never taken from the system locale: month heading `marec 2009`, day heading `14. 3. 2009`, time `18:42`.
- Post kinds: `KINDS = ("timeline", "others-timeline", "groups", "life-events")`.
- Run folder: `<out>/book_YYYY-MM-DD_HHMM/`, with `images/`, `markdown/`, `book.pdf`, `book.epub`, `print/book.typ`, `print/book.tex`, `params.json`.
- `output/` is git-ignored. Never commit anything from the owner's export: the fixture is synthetic.
- Tests: `python -m unittest -v` from the repo root.

## Review Focus

1. **A friend's comment containing `:::` at line start** must not close the note div early and leak the rest into the book. Escape it in notes too (test in Task 2).
2. **An export path that isn't the export root** (the zip itself, or a subfolder) gives a clear error naming the expected file, not a traceback (test in Task 6).
3. **An image listed in the JSON but missing on disk** prints a warning on stderr and is skipped. The run still finishes (test in Task 2).
4. **Two runs started in the same minute** don't overwrite each other: the second folder gets a `_2` suffix (test in Task 2).
5. **A post with only a timestamp** (no text, no photo; or video only) produces no entry and no empty heading in the book (test in Task 6).

---

### Task 1: Project setup, data model, text repair

**Files:**
- Delete: `face2book.py`, `run_all.sh`
- Create: `mise.toml`, `.gitignore`, `face2book/__init__.py` (empty), `face2book/export.py`, `tests/__init__.py` (empty), `tests/test_export.py`

**Interfaces:**
- Produces (in `face2book/export.py`):
  - `KINDS: tuple[str, ...]` (as in Global Constraints)
  - `class ExportError(Exception)`
  - `@dataclass class Post: when: datetime; text: str; images: list[Path]; kind: str; notes: list[str]`. `images` are relative to the export root. `notes` are `"Author: text"` strings.
  - `@dataclass class TimelineNote: when: datetime; author: str; text: str`
  - `fix_text(s: str) -> str`
  - `fix_strings(obj)`: walks dicts and lists from `json.load` and returns a copy with every `str` passed through `fix_text`

- [ ] **Step 1:** Write `mise.toml`:

```toml
[tools]
python = "3.15"
pandoc = "3"
typst = "0.15"
```

Run `mise install`, then `pandoc --version | head -1` and `typst --version`. Expected: pandoc 3.x, typst 0.15.x.

- [ ] **Step 2:** Write `.gitignore` with `output/`, `__pycache__/`. Then `git rm face2book.py run_all.sh`.

- [ ] **Step 3: Write the failing tests** in `tests/test_export.py`:

```python
def test_fix_text_repairs_mojibake(self):
    self.assertEqual(fix_text("Ä\u008d"), "č")
    self.assertEqual(fix_text("Å¾ivot"), "život")
def test_fix_text_leaves_good_text(self):
    self.assertEqual(fix_text("plain"), "plain")
    self.assertEqual(fix_text("čaj"), "čaj")      # not latin-1 encodable
    self.assertEqual(fix_text("café"), "café")    # latin-1 but not valid utf-8
def test_fix_strings_walks_nested(self):
    self.assertEqual(fix_strings({"a": ["Ä\u008d", 1, {"b": "Ä\u008d"}]}), {"a": ["č", 1, {"b": "č"}]})
```

- [ ] **Step 4:** Run `python -m unittest tests.test_export -v`. Expected: FAIL, import error.

- [ ] **Step 5:** Implement the Interfaces above. `fix_text` returns `s` unchanged on `UnicodeEncodeError`/`UnicodeDecodeError`.

- [ ] **Step 6:** Run `python -m unittest -v`. Expected: PASS.

- [ ] **Step 7:** Commit with the message `Rewrite: project setup, data model, mojibake fix`.

---

### Task 2: Markdown run folder

**Files:**
- Create: `face2book/markdown.py`, `tests/test_markdown.py`

**Interfaces:**
- Consumes: `Post`, `TimelineNote` from Task 1.
- Produces: `write_run(posts: list[Post], notes: list[TimelineNote], export_root: Path, out_root: Path, params: dict) -> Path`. It creates and returns the run folder, and writes `markdown/<year>.md`, `markdown/metadata.yaml`, `images/`, `params.json`.
  - `escape_md(s: str) -> str`

**Rules the code must follow:**
- Folder name: `book_` + `datetime.now().strftime("%Y-%m-%d_%H%M")`. If it exists, use `_2`, `_3`, and so on.
- One file per year, ordered by time. `# 2009`, `## marec 2009`, `### 14. 3. 2009`, then per post a paragraph starting with `*18:42* ` followed by the escaped text, then `![](../images/<name>)` per image, then the post's notes as one `::: note` div, with one `**Author:** text` paragraph per note (author and text both escaped). A note string splits on the first `": "`.
- Friends' `TimelineNote`s go into a `::: note` div under their day heading, after that day's posts.
- When a year, month or day holds no `Post`, its heading is written inside its own `::: note` div, so the filter removes it too.
- `escape_md`: backslash-escape ``\ ` * _ [ ] < > # | ~ ^ $``. At line start, also escape `:`, `-`, `+`, `=` and `\d+\.`. Turn each newline into a hard break (`\` + newline). Plain text like `18:42` or `Ahoj, ako sa máš?` must read unchanged.
- Images: copy `export_root / img` to `images/<basename>`. If the name is taken by a different source, use `<stem>-2<suffix>`. If the source file is missing, print `warning: missing image <path>` to stderr and skip it.
- `metadata.yaml`: `title: Facebook <first year>–<last year>`, `author: ""`, `lang: sk`.
- `params.json`: `params` dumped as JSON with `ensure_ascii=False, indent=2`.

- [ ] **Step 1: Write the failing tests** in `tests/test_markdown.py`. Build `Post`s in code in a `tempfile.TemporaryDirectory`, with one fake JPEG file in the fake export root. Tests:

```python
test_headings_slovak          # "# 2009", "## marec 2009", "### 14. 3. 2009", "*18:42* " in 2009.md
test_notes_in_note_div        # "::: note\n**Jana:** Super!" present; "Super!" appears nowhere outside a note div
test_note_with_fence_is_escaped   # note text ":::\nleak" → no line in the file equals ":::" except div fences you wrote (count fences == 2 * number of note divs)
test_note_only_day_heading_inside_note   # TimelineNote on 15. 3. 2009, no post that day → "::: note\n### 15. 3. 2009" present
test_escape_md                # escape_md("a*b_c") == r"a\*b\_c"; escape_md("18:42") == "18:42"; escape_md("- x") == r"\- x"; escape_md("a\nb") == "a\\\nb"
test_images_copied_and_missing_warns   # existing image copied to images/, missing one → stderr "warning: missing image", no exception
test_run_folder_collision     # two write_run calls in the same minute → second folder ends with "_2"
test_params_json_written      # json.load(run/"params.json") == params
```

- [ ] **Step 2:** Run `python -m unittest tests.test_markdown -v`. Expected: FAIL, import error.
- [ ] **Step 3:** Implement `write_run` and `escape_md` following the rules above.
- [ ] **Step 4:** Run `python -m unittest -v`. Expected: PASS.
- [ ] **Step 5:** Commit with the message `Rewrite: Markdown run folder writer`.

---

### Task 3: Build finished formats without notes

**Files:**
- Create: `face2book/drop_notes.lua`, `face2book/build.py`, `tests/test_build.py`

**Interfaces:**
- Consumes: run folder layout from Task 2 (use `write_run` in the test).
- Produces: `build(run_dir: Path) -> None`, which writes `book.epub`, `book.pdf`, `print/book.typ`, `print/book.tex`. If `pandoc` or `typst` isn't on `PATH` (`shutil.which`), it raises `SystemExit("pandoc/typst not found: run `mise install`")`. If pandoc fails, it raises `SystemExit` with pandoc's stderr.

`drop_notes.lua` is exactly:

```lua
function Div(el)
  if el.classes:includes("note") then return {} end
end
```

`build.py` runs pandoc with `cwd=run_dir/"markdown"`. Inputs are `metadata.yaml` followed by the year files sorted by name. Common args: `--lua-filter <abs path to drop_notes.lua> --resource-path .`. The four calls:
- `-o ../book.epub`
- `--pdf-engine=typst -o ../book.pdf`
- `-t typst -s -o ../print/book.typ`
- `-t latex -s -o ../print/book.tex`

`../images/...` paths then resolve from both `markdown/` and `print/`.

- [ ] **Step 1: Write the failing test** `test_notes_never_reach_book`. Use `write_run` with one post `"Môj text"` carrying the note `"Jana: TAJNE_SLOVA"`, plus a `TimelineNote` on a note-only day with the text `"TAJNE_DRUHE"` and a day of 16. 3. 2009. Call `build`. Assert:
  - all four files exist;
  - `"Môj text"` is in `print/book.typ`;
  - none of `TAJNE_SLOVA`, `TAJNE_DRUHE`, `16. 3. 2009` appear in `print/book.typ`, `print/book.tex`, or any `.xhtml` inside `book.epub` (read with `zipfile`).

  This test must **fail**, not skip, when pandoc is missing.
  PDF text is not checked, because it is compiled from the same filtered document. Add a `ponytail:` comment saying so.
- [ ] **Step 2:** Run `python -m unittest tests.test_build -v`. Expected: FAIL, import error.
- [ ] **Step 3:** Implement `drop_notes.lua` and `build`.
- [ ] **Step 4:** Run `python -m unittest -v`. Expected: PASS. Open the PDF once by eye: `xdg-open` it and check that it has diacritics and no notes.
- [ ] **Step 5:** Commit with the message `Rewrite: pandoc build with note filter`.

---

### Task 4: CLI and guided menu

**Files:**
- Create: `face2book/__main__.py`, `face2book/menu.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `build` (Task 3), `write_run` (Task 2), and `load` (Task 6; import it inside the `extract` branch so this task works before Task 6 exists).
- Produces:
  - `main(argv: list[str] | None = None) -> int` in `__main__.py`. Subcommands:
    - `extract <export_dir> [--out output] [--tz Europe/Bratislava] [--include timeline,others-timeline,groups,life-events] [--from YEAR] [--to YEAR]` → `load` → `write_run` → `build`. Prints the run folder path.
    - `build <run_dir>` → `build`.
    - No arguments → `main(menu(Path("output")))`.
    - `--include` values outside `KINDS` exit with an argparse error. `params` = `{"export": abs path, "include": [...], "from": int|None, "to": int|None, "tz": str}`.
  - `menu(out_root: Path, ask: Callable[[str], str] = input) -> list[str]` in `menu.py`. It returns argv for `main`. Prompts, in order:
    1. Action: `1) new run from export  2) rebuild existing run`.
    2. For rebuild: a numbered list of `out_root/book_*` folders, newest first.
    3. For a new run: export path, then kinds as numbered toggles (enter numbers to flip, empty to accept), then from year, to year and timezone.

    Every default comes from the newest `out_root/book_*/params.json`, if one exists. Empty input keeps the default, and is shown as `[default]` in the prompt.

- [ ] **Step 1: Write the failing tests** in `tests/test_cli.py`:

```python
test_main_build_calls_build            # patch face2book.__main__.build; main(["build", "x"]) == 0; called with Path("x")
test_main_rejects_unknown_kind         # main(["extract", "e", "--include", "bogus"]) raises SystemExit
test_menu_defaults_from_last_params    # out_root/book_2026-01-01_1200/params.json with include=["timeline"], from=2010;
                                       # menu(out_root, ask=iter(["1", "", "", "", "", ""]).__next__)
                                       # == ["extract", <export from params>, "--include", "timeline", "--from", "2010", "--tz", "Europe/Bratislava", "--out", str(out_root)]
test_menu_toggle_kind                  # answering "2" at the kinds prompt adds others-timeline
test_menu_rebuild_lists_runs           # answers ["2", "1"] → ["build", str(newest run dir)]
```

  `None` year values are omitted from argv.
- [ ] **Step 2:** Run `python -m unittest tests.test_cli -v`. Expected: FAIL.
- [ ] **Step 3:** Implement `main` and `menu`.
- [ ] **Step 4:** Run `python -m unittest -v`. Expected: PASS.
- [ ] **Step 5:** Commit with the message `Rewrite: CLI and guided menu`.

---

### Task 5: Inspect the owner's export (BLOCKED until the owner gives the path)

**Files:**
- Create: `docs/export-layout.md`, `tests/fixture.py`

**Interfaces:**
- Produces: `make_export(root: Path) -> None` in `tests/fixture.py`. It writes a minimal **synthetic** export using the real file paths and keys. It covers: one post per kind the export can distinguish, mojibake text (`"Ä\u008d"`), a share-only post, a video-only post, a timestamp-only post, a photo with a friend comment and an owner reply, a friend's timeline post on a day with no owner post, text with `* # < :::`, and an image file referenced but not present.

- [ ] **Step 1:** List the export's JSON files: `find <export> -name '*.json' | sort`. For each candidate (posts, groups, life events, other people's posts on the timeline, comments), print its key structure with no content, for example `python -I -c "import json,sys; ..."`. Print key names and types only. Never print or commit post text.
- [ ] **Step 2:** Write `docs/export-layout.md`. For each of the 4 kinds and for friends' timeline posts and comments, give the file path and the JSON keys holding time, text, images and author. For each kind, say how it is told apart structurally. A kind that can't be told apart is merged into `timeline`, and this file says so. Also list what is missing from the export, for example comments on text-only posts.
- [ ] **Step 3:** Write `tests/fixture.py` from that layout.
- [ ] **Step 4:** Commit with the message `Document export layout, add synthetic fixture`.

---

### Task 6: Load the export

**Files:**
- Modify: `face2book/export.py`
- Test: `tests/test_export.py`

**Interfaces:**
- Consumes: `docs/export-layout.md` and `make_export` from Task 5; the dataclasses from Task 1.
- Produces: `load(export_root: Path, tz: ZoneInfo, include: set[str], year_from: int | None, year_to: int | None) -> tuple[list[Post], list[TimelineNote]]`, both lists sorted by `when`.
  - Raises `ExportError(f"not a Facebook JSON export: {expected} missing")` when the main posts file is absent.
  - Keep rule: keep a post when it has owner text or at least one photo. Videos are dropped (judge by file extension: `.mp4 .mov .webm`). An empty `data` entry adds no text.
  - The owner's comments on other people's posts are not loaded.

- [ ] **Step 1: Write the failing tests**, all using `make_export`:

```python
test_load_drops_share_video_and_empty   # no Post with text=="" and images==[]
test_load_fixes_mojibake                # some Post.text contains "č"
test_load_include_filters_kinds         # include={"timeline"} → all p.kind == "timeline"
test_load_year_range                    # year_from=year_to=<fixture year> → all p.when.year == that
test_load_comments_are_notes            # photo post has friend comment and owner reply in notes, not in text
test_load_timeline_notes                # friend's timeline post returned as TimelineNote
test_load_wrong_root_raises             # load(root / "subdir", ...) raises ExportError mentioning the expected file
test_end_to_end                         # main(["extract", root, "--out", tmp]) == 0; book.epub exists; friend text absent from print/book.typ
```

- [ ] **Step 2:** Run `python -m unittest tests.test_export -v`. Expected: the new tests FAIL.
- [ ] **Step 3:** Implement `load` against `docs/export-layout.md`. Use `fix_strings(json.load(f))` on every file and `datetime.fromtimestamp(ts, tz)`.
- [ ] **Step 4:** Run `python -m unittest -v`. Expected: PASS.
- [ ] **Step 5:** Commit with the message `Rewrite: load Facebook export`.

---

### Task 7: Real run and README

**Files:**
- Create: `README.md`

- [ ] **Step 1:** Run `python -m face2book extract <owner export> --out output`. Expected: a run folder path is printed, and all four book files exist.
- [ ] **Step 2:** Run it again with `--include timeline --from 2010 --to 2010`. Expected: a second folder, and its `params.json` shows those values.
- [ ] **Step 3:** Run `grep -c '::: note' output/book_*/markdown/*.md` (notes exist), then check that one known friend's comment is absent from `print/book.typ`. Report counts only, never content.
- [ ] **Step 4:** Write `README.md` covering:
  - `mise install`;
  - `python -m face2book` (menu);
  - the two CLI commands;
  - the run folder layout;
  - "edit `markdown/`, then `build <run_dir>`";
  - the `::: note` rule;
  - which kinds were merged (from `docs/export-layout.md`).

  Keep it under 60 lines.
- [ ] **Step 5:** Commit with the message `Add README`. Hand the owner the two run folders to compare.
