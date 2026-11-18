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

