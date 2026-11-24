import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from face2book.__main__ import main
from face2book.menu import menu
from tests import fixture


def answers(*a):
    it = iter(a)
    return lambda _prompt: next(it)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        for cm in (contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO())):
            cm.__enter__()
            self.addCleanup(cm.__exit__, None, None, None)

    def make_run(self, name, **params):
        run = self.out / name
        run.mkdir()
        (run / "params.json").write_text(json.dumps(params))
        return run

    def test_extract_books_writes_one_run_per_range(self):
        export = self.out / "export"
        fixture.make_export(export)
        runs = self.out / "runs"
        with mock.patch("face2book.__main__.build"):
            code = main(["extract", str(export), "--out", str(runs), "--books", "2009-2009,2010-2010"])
        self.assertEqual(code, 0)
        parts = sorted((json.loads((r / "params.json").read_text()) for r in runs.iterdir()),
                       key=lambda p: p["part"])
        self.assertEqual([(p["part"], p["of"], p["years"]) for p in parts],
                         [(1, 2, [2009, 2009]), (2, 2, [2010, 2010])])

    def test_cover_image_without_file_exits_1(self):
        export = self.out / "export"
        fixture.make_export(export)
        err = io.StringIO()
        with contextlib.redirect_stderr(err), mock.patch("face2book.__main__.build"):
            code = main(["extract", str(export), "--out", str(self.out / "runs"), "--cover", "image"])
            missing = main(["extract", str(export), "--out", str(self.out / "runs"), "--cover", "image",
                            "--cover-image", str(self.out / "nope.png")])
        self.assertEqual((code, missing), (1, 1))
        self.assertEqual(err.getvalue().count("error: "), 2)

    def test_main_build_calls_build(self):
        (self.out / "markdown").mkdir()
        with mock.patch("face2book.__main__.build") as b:
            self.assertEqual(main(["build", str(self.out)]), 0)
        b.assert_called_once_with(self.out)

    def test_main_rejects_unknown_kind(self):
        with self.assertRaises(SystemExit):
            main(["extract", "e", "--include", "bogus"])

    def test_menu_defaults_from_last_params(self):
        self.make_run("book_2026-01-01_1200", export="/data/fb", include=["timeline"],
                      **{"from": 2010, "to": None, "tz": "Europe/Bratislava"})
        argv = menu(self.out, ask=answers("1", "", "", "", "", ""))
        self.assertEqual(argv, ["extract", "/data/fb", "--include", "timeline", "--from", "2010",
                                "--tz", "Europe/Bratislava", "--out", str(self.out)])

    def test_menu_toggle_kind(self):
        self.make_run("book_2026-01-01_1200", export="/data/fb", include=["timeline"])
        argv = menu(self.out, ask=answers("1", "", "2", "", "", "", ""))
        self.assertEqual(argv[argv.index("--include") + 1], "timeline,others-timeline")

    def test_menu_no_previous_run_reasks_export(self):
        argv = menu(self.out, ask=answers("1", "", "/e", "", "", "", ""))
        self.assertEqual(argv[1], "/e")
        self.assertEqual(argv[argv.index("--include") + 1],
                         "timeline,others-timeline,groups,life-events")

    def test_menu_rebuild_lists_runs(self):
        self.make_run("book_2026-01-01_1200", export="/a")
        newest = self.make_run("book_2026-02-01_1200", export="/a")
        self.assertEqual(menu(self.out, ask=answers("2", "1")), ["build", str(newest)])

    def test_menu_rebuild_reasks_bad_pick(self):
        run = self.make_run("book_2026-01-01_1200", export="/a")
        argv = menu(self.out, ask=answers("x", "2", "x", "0", "9", "1"))
        self.assertEqual(argv, ["build", str(run)])

    def test_menu_refuses_zero_kinds(self):
        self.make_run("book_2026-01-01_1200", export="/a", include=["timeline"])
        argv = menu(self.out, ask=answers("1", "", "1", "", "3", "", "", "", ""))
        self.assertEqual(argv[argv.index("--include") + 1], "groups")

    def test_main_build_missing_dir(self):
        self.assertEqual(main(["build", str(self.out / "nope")]), 1)

    def test_main_rejects_empty_include(self):
        with self.assertRaises(SystemExit):
            main(["extract", "e", "--include", ""])


if __name__ == "__main__":
    unittest.main()
