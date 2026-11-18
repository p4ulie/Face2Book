"""Build epub, pdf, typst and latex from a run's Markdown, dropping every note."""

import os
import shutil
import subprocess
from pathlib import Path

MISE = Path(__file__).resolve().parent.parent / "mise.toml"
# mise shims only resolve inside the repo; point them at the repo's tool versions from any cwd.
ENV = {**os.environ, "MISE_GLOBAL_CONFIG_FILE": str(MISE)}
FILTER = Path(__file__).with_name("drop_notes.lua").resolve()


def build(run_dir: Path) -> None:
    if not (shutil.which("pandoc") and shutil.which("typst")):
        raise SystemExit("pandoc/typst not found: run `mise install`")
    run_dir = Path(run_dir).resolve()
    md = run_dir / "markdown"
    (run_dir / "print").mkdir(exist_ok=True)
    sources = ["metadata.yaml"] + sorted(p.name for p in md.glob("*.md"))
    common = ["pandoc", *sources, "--lua-filter", str(FILTER), "--resource-path", "."]
    calls = [
        ["-o", "../book.epub"],
        ["-t", "typst", "-s", "-o", "../print/book.typ"],
        ["-t", "latex", "-s", "-o", "../print/book.tex"],
    ]
    for extra in calls:
        r = subprocess.run(common + extra, cwd=md, capture_output=True, text=True, encoding="utf-8", env=ENV)
        if r.returncode:
            raise SystemExit(r.stderr)
    # Ruling B: compile the filtered book.typ itself; root = run dir so ../images resolves.
    r = subprocess.run(["typst", "compile", "--root", str(run_dir), "print/book.typ", "book.pdf"],
                       cwd=run_dir, capture_output=True, text=True, encoding="utf-8", env=ENV)
    if r.returncode:
        raise SystemExit(r.stderr)
