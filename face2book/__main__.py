"""Command line: extract an export into a run folder and build it, or rebuild a run."""

import argparse
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from face2book.build import build
from face2book.export import KINDS, ExportError, load
from face2book.markdown import write_run
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
    sub.add_parser("build").add_argument("run_dir")
    a = ap.parse_args(argv)

    if a.cmd == "build":
        if not (Path(a.run_dir) / "markdown").is_dir():
            print(f"error: {a.run_dir} is not a run folder", file=sys.stderr)
            return 1
        build(Path(a.run_dir))
        return 0
    export_root = Path(a.export_dir).resolve()
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
              "from": a.year_from, "to": a.year_to, "tz": a.tz}
    run = write_run(posts, notes, export_root, Path(a.out), params)
    print(run)
    build(run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
