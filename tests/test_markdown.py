import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from face2book import markdown
from face2book.export import Post, TimelineNote
from face2book.markdown import escape_md, write_run


class MarkdownTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.export = Path(tmp.name) / "export"
        (self.export / "img").mkdir(parents=True)
        (self.export / "img" / "a.jpg").write_bytes(b"\xff\xd8fake")
        self.out = Path(tmp.name) / "out"

    def post(self, **kw):
        args = dict(when=datetime(2009, 3, 14, 18, 42), text="Ahoj", images=[],
                    kind="timeline", notes=[])
        args.update(kw)
        return Post(**args)

    def run_md(self, posts, notes=(), year="2009"):
        run = write_run(posts, list(notes), self.export, self.out, {})
        return (run / "markdown" / f"{year}.md").read_text(encoding="utf-8")

    def test_headings_slovak(self):
        md = self.run_md([self.post()])
        for s in ("# 2009", "## marec 2009", "### 14. 3. 2009", "*18:42* "):
            self.assertIn(s, md)

    def test_notes_in_note_div(self):
        md = self.run_md([self.post(notes=["Jana: Super!"])])
        self.assertIn("::: note\n**Jana:** Super!", md)
        self.assertEqual(md.count("Super!"), 1)

    def test_note_with_fence_is_escaped(self):
        md = self.run_md([self.post(notes=["Jana: :::\nleak"])],
                         [TimelineNote(datetime(2009, 3, 14, 20, 0), "Eva", ":::")])
        fences = [l for l in md.splitlines() if l.startswith(":::")]
        self.assertEqual(len(fences), 2 * 2)

    def test_note_only_day_heading_inside_note(self):
        md = self.run_md([self.post()],
                         [TimelineNote(datetime(2009, 3, 15, 9, 0), "Eva", "Hej")])
        self.assertIn("::: note\n### 15. 3. 2009\n:::", md)
        self.assertIn("**Eva:** Hej", md)

    def test_note_only_year_and_month_inside_note(self):
        md = self.run_md([self.post()],
                         [TimelineNote(datetime(2010, 5, 1, 9, 0), "Eva", "Hej")],
                         year="2010")
        self.assertIn("::: note\n# 2010\n:::", md)
        self.assertIn("::: note\n## máj 2010\n:::", md)

    def test_posts_sorted(self):
        md = self.run_md([self.post(text="late", when=datetime(2009, 3, 14, 20, 0)),
                          self.post(text="early")])
        self.assertLess(md.index("early"), md.index("late"))

    def test_escape_md(self):
        self.assertEqual(escape_md("a*b_c"), r"a\*b\_c")
        self.assertEqual(escape_md("18:42"), "18:42")
        self.assertEqual(escape_md("- x"), r"\- x")
        self.assertEqual(escape_md("a\nb"), "a\\\nb")
        self.assertEqual(escape_md("1. x"), r"1\. x")
        self.assertEqual(escape_md("Ahoj, ako sa máš?"), "Ahoj, ako sa máš?")

    def test_images_copied_and_missing_warns(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            run = write_run([self.post(images=[Path("img/a.jpg"), Path("img/gone.jpg")])],
                            [], self.export, self.out, {})
        self.assertTrue((run / "images" / "a.jpg").exists())
        self.assertIn("warning: missing image", err.getvalue())
        md = (run / "markdown" / "2009.md").read_text(encoding="utf-8")
        self.assertIn("![](../images/a.jpg)", md)
        self.assertNotIn("gone.jpg", md)

    def test_image_name_clash(self):
        (self.export / "img2").mkdir()
        (self.export / "img2" / "a.jpg").write_bytes(b"other")
        run = write_run([self.post(images=[Path("img/a.jpg"), Path("img2/a.jpg")])],
                        [], self.export, self.out, {})
        self.assertTrue((run / "images" / "a-2.jpg").exists())

    def test_run_folder_collision(self):
        fixed = datetime(2026, 1, 2, 3, 4)
        with mock.patch.object(markdown, "datetime") as dt:
            dt.now.return_value = fixed
            first = write_run([self.post()], [], self.export, self.out, {})
            second = write_run([self.post()], [], self.export, self.out, {})
        self.assertEqual(first.name, "book_2026-01-02_0304")
        self.assertEqual(second.name, "book_2026-01-02_0304_2")

    def test_params_json_written(self):
        params = {"title": "Kniha š"}
        run = write_run([self.post()], [], self.export, self.out, params)
        self.assertEqual(json.loads((run / "params.json").read_text(encoding="utf-8")), params)
        meta = (run / "markdown" / "metadata.yaml").read_text(encoding="utf-8")
        self.assertIn("title: Facebook 2009\n", meta)


if __name__ == "__main__":
    unittest.main()
