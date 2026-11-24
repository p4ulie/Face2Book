import unittest

from face2book.export import fix_strings, fix_text


class FixTextTests(unittest.TestCase):
    def test_fix_text_repairs_mojibake(self):
        self.assertEqual(fix_text("Ä\u008d"), "č")
        self.assertEqual(fix_text("Å¾ivot"), "život")

    def test_fix_text_leaves_good_text(self):
        self.assertEqual(fix_text("plain"), "plain")
        self.assertEqual(fix_text("čaj"), "čaj")      # not latin-1 encodable
        self.assertEqual(fix_text("café"), "café")    # latin-1 but not valid utf-8

    def test_fix_strings_walks_nested(self):
        self.assertEqual(
            fix_strings({"a": ["Ä\u008d", 1, {"b": "Ä\u008d"}]}),
            {"a": ["č", 1, {"b": "č"}]},
        )



import contextlib
import io
import json
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

from face2book.__main__ import main
from face2book.export import KINDS, ExportError, load
from tests import fixture as fx

TZ = ZoneInfo("Europe/Bratislava")


class LoadTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        fx.make_export(self.root)

    def load(self, include=KINDS, a=None, b=None):
        return load(self.root, TZ, set(include), a, b)

    def test_load_drops_share_video_and_empty(self):
        posts, _ = self.load()
        self.assertFalse([p for p in posts if p.text == "" and not p.images])
        self.assertFalse([p for p in posts if any(str(i).endswith(".mp4") for i in p.images)])

    def test_load_fixes_mojibake(self):
        posts, _ = self.load()
        self.assertTrue(any("č" in p.text for p in posts))
        self.assertIn(fx.MOJIBAKE_TEXT, [p.text for p in posts])

    def test_load_include_filters_kinds(self):
        posts, notes = self.load({"timeline"})
        self.assertTrue(posts and all(p.kind == "timeline" for p in posts))
        self.assertEqual({p.kind for p in self.load()[0]}, set(KINDS))

    def test_load_year_range(self):
        posts, notes = self.load(a=fx.YEAR, b=fx.YEAR)
        self.assertTrue(all(p.when.year == fx.YEAR for p in posts + notes))
        self.assertNotIn(fx.LATER_TEXT, [p.text for p in posts])

    def test_load_comments_are_notes(self):
        posts, _ = self.load()
        p = next(p for p in posts if p.text == fx.PHOTO_TEXT)
        self.assertEqual(p.notes, [f"{fx.FRIEND}: {fx.FRIEND_COMMENT}", f"{fx.OWNER}: {fx.OWNER_REPLY}"])
        self.assertNotIn(fx.FRIEND_COMMENT, p.text)
        self.assertEqual(p.images, [Path(fx.PHOTO)])

    def test_load_timeline_notes(self):
        _, notes = self.load()
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].text, fx.FRIEND_WALL_TEXT)
        self.assertIn(fx.FRIEND, notes[0].author)

    def test_load_life_event_name_fallback(self):
        posts, _ = self.load({"life-events"})
        self.assertEqual([p.text for p in posts], [fx.LIFE_TITLE])

    def test_load_life_event_single_record(self):
        f = self.root / "personal_information/profile_information/your_experiences.json"
        f.write_text(json.dumps(json.loads(f.read_text())[0]))
        posts, _ = self.load({"life-events"})
        self.assertEqual([p.text for p in posts], [fx.LIFE_TITLE])

    def test_load_wrong_root_raises(self):
        with self.assertRaises(ExportError) as c:
            load(self.root / "subdir", TZ, set(KINDS), None, None)
        self.assertIn("your_posts__check_ins__photos_and_videos_1.json", str(c.exception))

    def test_unsupported_image_warns(self):
        f = self.root / fx.POSTS_FILE
        data = json.loads(f.read_text())
        data.append({"timestamp": fx.ts(7, 1), "title": "x", "data": [{"post": "Hi"}],
                     "attachments": [{"data": [{"media": fx.media("a/b.tiff", 1)},
                                               {"media": fx.media("a/d.avif", 1)},
                                               {"media": fx.media("a/c.JPG", 1)}]}]})
        f.write_text(json.dumps(data))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            posts, _ = self.load({"timeline"})
        p = next(p for p in posts if p.text == "Hi")
        self.assertEqual(p.images, [Path("a/d.avif"), Path("a/c.JPG")])
        self.assertEqual(err.getvalue().strip(), "warning: unsupported image a/b.tiff")

    def test_extract_no_posts_returns_1(self):
        out = self.root / "out"
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main(["extract", str(self.root), "--from", "2099", "--out", str(out)])
        self.assertEqual(rc, 1)
        self.assertIn("no posts match", err.getvalue())
        self.assertFalse(list(out.glob("book_*")))

    def test_extract_bad_tz_exits_cleanly(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as c:
            main(["extract", str(self.root), "--tz", "Europe/Bratislav"])
        self.assertNotEqual(c.exception.code, 0)
        self.assertIn("unknown time zone", err.getvalue())

    def test_end_to_end(self):
        out = self.root / "out"
        shown = io.StringIO()
        with contextlib.redirect_stdout(shown), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["extract", str(self.root), "--out", str(out)]), 0)
        self.assertRegex(shown.getvalue(), r"timeline\s+\d+\s+\d+\n")
        self.assertRegex(shown.getvalue(), r"oldest \d{4}-\d{2}-\d{2}   newest \d{4}-\d{2}-\d{2}")
        run = next(out.iterdir())
        self.assertTrue((run / "book.epub").exists())
        self.assertNotIn(fx.FRIEND_WALL_TEXT, (run / "print" / "book.typ").read_text())
