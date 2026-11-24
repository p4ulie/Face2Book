"""Command line: extract an export into a run folder and build it, or rebuild a run."""

import argparse
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from face2book.build import build
from face2book.export import KINDS, ExportError, load, parse_years
from face2book.markdown import book_title, write_run
from face2book.menu import menu


def kinds(value: str) -> list[str]:
    chosen = [k for k in value.split(",") if k]
    bad = [k for k in chosen if k not in KINDS]
    if not chosen:
        raise argparse.ArgumentTypeError("choose at least one kind")
    if bad:
        raise argparse.ArgumentTypeError(f"unknown kind {bad[0]!r}, choose from {', '.join(KINDS)}")
    return chosen


def tz(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise argparse.ArgumentTypeError(f"unknown time zone {value!r}") from None
    return value


def summary(posts, notes, include) -> str:
    rows = [f"{'kind':<16}{'posts':>7}{'images':>8}"]
    for kind in KINDS:
        if kind in include:
            mine = [p for p in posts if p.kind == kind]
            rows.append(f"{kind:<16}{len(mine):>7}{sum(len(p.images) for p in mine):>8}")
    rows.append(f"{'timeline notes':<16}{len(notes):>7}")
    dates = [x.when for x in posts + notes]
    rows.append(f"oldest {min(dates):%Y-%m-%d}   newest {max(dates):%Y-%m-%d}")
    return "\n".join(rows)


def cover_args(a) -> dict:
    return {"cover": None if a.cover == "none" else a.cover, "cover_image": a.cover_image,
            "title_page": a.title_page}


def extract_books(a, export_root: Path) -> int:
    for part, (first, last) in enumerate(a.books, 1):
        try:
            posts, notes = load(export_root, ZoneInfo(a.tz), set(a.include), first, last)
        except ExportError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        if not posts:
            print(f"part {part} ({first}-{last}): no posts, skipped")
            continue
        print(summary(posts, notes, a.include))
        params = {"export": str(export_root), "include": a.include, "from": first, "to": last,
                  "tz": a.tz, "part": part, "of": len(a.books), "years": [first, last],
                  "cover": a.cover, "title_page": a.title_page}
        title = book_title(sorted({x.when.year for x in posts + notes}), part, len(a.books))
        run = write_run(posts, notes, export_root, Path(a.out), params, title=title, **cover_args(a))
        print(run)
        build(run)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return main(menu(Path("output")))
    ap = argparse.ArgumentParser(prog="face2book")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("extract")
    ex.add_argument("export_dir")
    ex.add_argument("--out", default="output")
    ex.add_argument("--tz", type=tz, default="Europe/Bratislava")
    ex.add_argument("--include", type=kinds, default=list(KINDS))
    ex.add_argument("--from", dest="year_from", type=int)
    ex.add_argument("--to", dest="year_to", type=int)
    ex.add_argument("--books", type=parse_years)
    ex.add_argument("--cover", choices=["none", "text", "image"], default="none")
    ex.add_argument("--cover-image", type=Path)
    ex.add_argument("--title-page", action="store_true")
    sub.add_parser("build").add_argument("run_dir")
    a = ap.parse_args(argv)

    if a.cmd == "build":
        if not (Path(a.run_dir) / "markdown").is_dir():
            print(f"error: {a.run_dir} is not a run folder", file=sys.stderr)
            return 1
        build(Path(a.run_dir))
        return 0
    if a.cover == "image" and not (a.cover_image and a.cover_image.is_file()):
        print("error: --cover image needs --cover-image with an existing file", file=sys.stderr)
        return 1
    export_root = Path(a.export_dir).resolve()
    if a.books:
        return extract_books(a, export_root)
    try:
        posts, notes = load(export_root, ZoneInfo(a.tz), set(a.include), a.year_from, a.year_to)
    except ExportError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if not posts:
        print("error: no posts match these options", file=sys.stderr)
        return 1
    print(summary(posts, notes, a.include))
    params = {"export": str(export_root), "include": a.include,
              "from": a.year_from, "to": a.year_to, "tz": a.tz,
              "cover": a.cover, "title_page": a.title_page}
    title = book_title(sorted({x.when.year for x in posts + notes}))
    run = write_run(posts, notes, export_root, Path(a.out), params, title=title, **cover_args(a))
    print(run)
    build(run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
