"""Build epub, pdf, typst and latex from a run's Markdown, dropping every note."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

MISE = Path(__file__).resolve().parent.parent / "mise.toml"
# mise shims only resolve inside the repo; point them at the repo's tool versions from any cwd.
ENV = {**os.environ, "MISE_GLOBAL_CONFIG_FILE": str(MISE)}
FILTER = Path(__file__).with_name("drop_notes.lua").resolve()
FIT = Path(__file__).with_name("fit_images.lua").resolve()


def build(run_dir: Path) -> None:
    if not (shutil.which("pandoc") and shutil.which("typst")):
        raise SystemExit("pandoc/typst not found: run `mise install`")
    run_dir = Path(run_dir).resolve()
    md = run_dir / "markdown"
    (run_dir / "print").mkdir(exist_ok=True)
    sources = sorted(p.name for p in md.glob("*.md"))
    if not sources:
        raise SystemExit(f"no Markdown files in {md}")
    common = ["pandoc", *sources, "--metadata-file=metadata.yaml", "-f", "markdown-citations", "--lua-filter", str(FILTER), "--resource-path", "."]
    calls = [
        ["-o", "../book.epub"],
        ["-t", "typst", "-s", "--lua-filter", str(FIT), "-o", "../print/book.typ"],
        ["-t", "latex", "-s", "-o", "../print/book.tex"],
    ]
    steps = [(common + extra, md, extra[-1]) for extra in calls]
    # Ruling B: compile the filtered book.typ itself; root = run dir so ../images resolves.
    steps.append((["typst", "compile", "--root", str(run_dir), "print/book.typ", "book.pdf"], run_dir, "book.pdf"))
    for cmd, cwd, output in steps:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                           env=ENV, stdin=subprocess.DEVNULL)
        if r.returncode:
            raise SystemExit(f"{output}: {r.stderr}")
        if r.stderr:
            print(f"{output}: {r.stderr}", file=sys.stderr)
