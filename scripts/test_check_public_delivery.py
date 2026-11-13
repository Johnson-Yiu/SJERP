import unittest
from check_public_delivery import DATABASE, RULES
import re


class RulesTest(unittest.TestCase):
    def test_synthetic_token(self):
        pattern = RULES["github-token"]
        self.assertIsNotNone(re.search(pattern, b"gh" + b"p_" + b"A" * 36))
        self.assertIsNone(re.search(pattern, b"gh" + b"p_PLACEHOLDER"))

    def test_database_sidecars(self):
        self.assertIsNotNone(DATABASE.search("local/test.sqlite3-wal"))
        self.assertIsNone(DATABASE.search("docs/test.sqlite3.md"))
