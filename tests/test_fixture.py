import json
import tempfile
import unittest
from pathlib import Path

from tests import fixture


class FixtureTest(unittest.TestCase):
    def test_make_export_writes_parseable_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture.make_export(root)
            for rel in (fixture.POSTS_FILE,
                        "your_facebook_activity/posts/posts_on_other_pages_and_profiles.json",
                        "your_facebook_activity/groups/group_posts_and_comments.json",
                        "personal_information/profile_information/your_experiences.json"):
                json.loads((root / rel).read_text())
            self.assertTrue((root / fixture.PHOTO).exists())
            self.assertFalse((root / fixture.MISSING_PHOTO).exists())
            raw = (root / fixture.POSTS_FILE).read_text()
            self.assertIn("\\u00c4\\u008d", raw)  # "č" stored as mojibake


if __name__ == "__main__":
    unittest.main()
