import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from face2book.__main__ import main
from face2book.menu import menu


def answers(*a):
    return iter(a).__next__


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)

    def make_run(self, name, **params):
        run = self.out / name
        run.mkdir()
        (run / "params.json").write_text(json.dumps(params))
        return run

    def test_main_build_calls_build(self):
        with mock.patch("face2book.__main__.build") as b:
            self.assertEqual(main(["build", "x"]), 0)
        b.assert_called_once_with(Path("x"))

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
        argv = menu(self.out, ask=answers("1", "", "2", "", "", ""))
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


if __name__ == "__main__":
    unittest.main()
