import shutil
import struct
import tempfile
import unittest
import zipfile
import zlib
from datetime import datetime
from pathlib import Path

from face2book.build import build
from face2book.export import Post, TimelineNote
from face2book.markdown import write_run

def png() -> bytes:
    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00")) + chunk(b"IEND", b""))


SECRETS = ["TAJNE_SLOVA", "TAJNE_DRUHE", "TAJNE_TRETIE", "16. 3. 2009"]


class BuildTest(unittest.TestCase):
    def test_notes_never_reach_book(self):
        # Fail, not skip, when the tools are missing.
        self.assertTrue(shutil.which("pandoc") and shutil.which("typst"), "pandoc/typst missing")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        export = Path(tmp.name) / "export"
        (export / "img").mkdir(parents=True)
        (export / "img" / "a.png").write_bytes(png())
        post = Post(datetime(2009, 3, 14, 18, 42), "Môj text", [Path("img/a.png")], "timeline",
                    ["Jana: TAJNE_SLOVA", "Peter: :::\nTAJNE_TRETIE"])
        note = TimelineNote(datetime(2009, 3, 16, 9, 0), "Eva", "TAJNE_DRUHE")
        run = write_run([post], [note], export, Path(tmp.name) / "out", {})
        build(run)
        for f in ("book.epub", "book.pdf", "print/book.typ", "print/book.tex"):
            self.assertTrue((run / f).is_file(), f)
        typ = (run / "print/book.typ").read_text(encoding="utf-8")
        self.assertIn("Môj text", typ)
        self.assertIn("a.png", typ)
        for bad in ("lang: sk", "title: Facebook"):
            self.assertNotIn(bad, typ)
        self.assertIn("title: [Facebook 2009]", typ)
        self.assertIn('#set image(fit: "contain")', typ)
        self.assertIn("height: 60.0%", typ)
        # ponytail: PDF text not checked, it is compiled from the same filtered book.typ.
        with zipfile.ZipFile(run / "book.epub") as z:
            self.assertTrue(any(n.startswith("EPUB/media/") for n in z.namelist()))
            self.assertIn("<dc:title", z.read("EPUB/content.opf").decode("utf-8"))
            texts = [z.read(n).decode("utf-8") for n in z.namelist() if n.endswith(".xhtml")]
        texts += [typ, (run / "print/book.tex").read_text(encoding="utf-8")]
        for s in SECRETS:
            for t in texts:
                self.assertNotIn(s, t)
        self.assertTrue((run / "book.pdf").read_bytes().startswith(b"%PDF"))

    def test_empty_markdown_dir_exits(self):
        self.assertTrue(shutil.which("pandoc") and shutil.which("typst"), "pandoc/typst missing")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        (Path(tmp.name) / "markdown").mkdir()
        with self.assertRaises(SystemExit):
            build(Path(tmp.name))

    def test_handles_stay_text(self):
        self.assertTrue(shutil.which("pandoc") and shutil.which("typst"), "pandoc/typst missing")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        post = Post(datetime(2009, 3, 14, 18, 42), "Ahoj @jana_test a [@x] a a@b.sk", [], "timeline", [])
        run = write_run([post], [], Path(tmp.name), Path(tmp.name) / "out", {})
        build(run)
        self.assertTrue((run / "book.pdf").is_file())
        typ = (run / "print/book.typ").read_text(encoding="utf-8")
        self.assertIn("@jana", typ)
        self.assertNotIn("#cite", typ)
