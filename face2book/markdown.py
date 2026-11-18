"""Write the editable Markdown master copy of the book (one folder per run)."""

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from face2book.export import Post, TimelineNote

MONTHS = ["január", "február", "marec", "apríl", "máj", "jún", "júl",
          "august", "september", "október", "november", "december"]


def escape_md(s: str) -> str:
    s = re.sub(r"([\\`*_\[\]<>#|~^$])", r"\\\1", s)
    lines = []
    for line in s.split("\n"):
        line = re.sub(r"^([:+=-])", r"\\\1", line)
        line = re.sub(r"^(\d+)\.", r"\1\\.", line)
        lines.append(line)
    return "\\\n".join(lines)


def note_div(*paragraphs: str) -> str:
    return "::: note\n" + "\n\n".join(paragraphs) + "\n:::"


def heading(text: str, has_post: bool) -> str:
    return text if has_post else note_div(text)


def make_run_folder(out_root: Path) -> Path:
    out_root.mkdir(parents=True, exist_ok=True)
    base = "book_" + datetime.now().strftime("%Y-%m-%d_%H%M")
    n = 1
    while True:
        run = out_root / (base if n == 1 else f"{base}_{n}")
        try:
            run.mkdir()
            return run
        except FileExistsError:
            n += 1


def copy_image(rel: Path, export_root: Path, images: Path, taken: dict) -> str | None:
    src = export_root / rel
    if not src.is_file():
        print(f"warning: missing image {src}", file=sys.stderr)
        return None
    name, n = src.name, 2
    while taken.get(name, src) != src:
        name = f"{src.stem}-{n}{src.suffix}"
        n += 1
    if name not in taken:
        taken[name] = src
        shutil.copy2(src, images / name)
    return name


def post_blocks(post: Post, export_root: Path, images: Path, taken: dict) -> list[str]:
    pics = [n for n in (copy_image(r, export_root, images, taken) for r in post.images) if n]
    if not post.text and not pics:
        return []
    blocks = [f"*{post.when:%H:%M}* " + escape_md(post.text)]
    blocks += [f"![](../images/{n})" for n in pics]
    if post.notes:
        paras = []
        for note in post.notes:
            author, sep, text = note.partition(": ")
            paras.append(f"**{escape_md(author)}:** {escape_md(text)}" if sep else escape_md(note))
        blocks.append(note_div(*paras))
    return blocks


def year_markdown(year: int, posts: list[Post], notes: list[TimelineNote],
                  export_root: Path, images: Path, taken: dict) -> str:
    # Headings depend on what is actually written, so build days first.
    months = []
    for month in sorted({x.when.month for x in posts + notes}):
        days = []
        for day in sorted({x.when.day for x in posts + notes if x.when.month == month}):
            body = []
            for p in posts:
                if (p.when.month, p.when.day) == (month, day):
                    body += post_blocks(p, export_root, images, taken)
            has_post = bool(body)
            dnotes = [n for n in notes if (n.when.month, n.when.day) == (month, day)]
            if dnotes:
                body.append(note_div(*(
                    f"**{escape_md(n.author)}:** {escape_md(n.text)}" for n in dnotes)))
            if body:
                days.append((day, has_post, [heading(f"### {day}. {month}. {year}", has_post)] + body))
        if days:
            months.append((month, any(d[1] for d in days), days))
    blocks = [heading(f"# {year}", any(m[1] for m in months))]
    for month, has_post, days in months:
        blocks.append(heading(f"## {MONTHS[month - 1]} {year}", has_post))
        for d in days:
            blocks += d[2]
    return "\n\n".join(blocks) + "\n"


def write_run(posts: list[Post], notes: list[TimelineNote], export_root: Path,
              out_root: Path, params: dict) -> Path:
    run = make_run_folder(out_root)
    (run / "markdown").mkdir()
    (run / "images").mkdir()
    posts = sorted(posts, key=lambda p: p.when)
    notes = sorted(notes, key=lambda n: n.when)
    taken: dict = {}
    years = sorted({x.when.year for x in posts + notes})
    for year in years:
        md = year_markdown(year, [p for p in posts if p.when.year == year],
                           [n for n in notes if n.when.year == year],
                           export_root, run / "images", taken)
        (run / "markdown" / f"{year}.md").write_text(md, encoding="utf-8")
    title = "Facebook"
    if years:
        title += f" {years[0]}" if years[0] == years[-1] else f" {years[0]}–{years[-1]}"
    (run / "markdown" / "metadata.yaml").write_text(
        f'title: {title}\nauthor: ""\nlang: sk\n', encoding="utf-8")
    (run / "params.json").write_text(
        json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
    return run
