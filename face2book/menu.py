"""Guided menu: asks the questions, returns argv for main()."""

import json
from pathlib import Path
from typing import Callable

from face2book.export import KINDS


def runs(out_root: Path) -> list[Path]:
    # names are timestamps, so name order is time order
    return sorted((p for p in out_root.glob("book_*") if p.is_dir()), reverse=True)


def last_params(out_root: Path) -> dict:
    for run in runs(out_root):
        try:
            return json.loads((run / "params.json").read_text())
        except (OSError, ValueError):
            continue
    return {}


def ask_default(ask: Callable[[str], str], label: str, default: str) -> str:
    return ask(f"{label} [{default}]: " if default else f"{label}: ").strip() or default


def pick(ask: Callable[[str], str], label: str, count: int, default: bool = False) -> int | None:
    """Ask for a number 1..count until valid; empty returns None when default is True."""
    while True:
        answer = ask(label).strip()
        if not answer and default:
            return None
        if answer.isdecimal() and 1 <= int(answer) <= count:
            return int(answer)
        print(f"Enter a number from 1 to {count}.")


def menu(out_root: Path, ask: Callable[[str], str] = input) -> list[str]:
    print("1) new run from export  2) rebuild existing run")
    if pick(ask, "Action: ", 2) == 2:
        found = runs(out_root)
        if not found:
            raise SystemExit(f"no runs in {out_root}")
        for i, run in enumerate(found, 1):
            print(f"{i}) {run.name}")
        return ["build", str(found[pick(ask, "Run: ", len(found)) - 1])]

    p = last_params(out_root)
    export = ""
    while not export:
        export = ask_default(ask, "Export folder", p.get("export", ""))
    on = set(p.get("include", KINDS))
    while True:
        for i, kind in enumerate(KINDS, 1):
            print(f"{i}) [{'x' if kind in on else ' '}] {kind}")
        n = pick(ask, "Number to toggle, empty to accept: ", len(KINDS), default=True)
        if n:
            on ^= {KINDS[n - 1]}
        elif on:
            break
        else:
            print("Select at least one kind.")
    argv = ["extract", export, "--include", ",".join(k for k in KINDS if k in on)]
    for flag, key in (("--from", "from"), ("--to", "to")):
        year = ask_default(ask, f"{flag[2:].capitalize()} year (empty for none)", str(p.get(key) or ""))
        if year:
            argv += [flag, year]
    tz = ask_default(ask, "Timezone", p.get("tz", "Europe/Bratislava"))
    return argv + ["--tz", tz, "--out", str(out_root)]
