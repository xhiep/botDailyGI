from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from botdailygi.services import codes


class CodesTests(unittest.TestCase):
    def test_load_blacklist_reuses_empty_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            blacklist_file = Path(temp_dir) / "codes-blacklist.txt"
            blacklist_file.write_text("", encoding="utf-8")
            codes.invalidate_blacklist_cache()

            with patch("botdailygi.services.codes.CODES_BLACKLIST_FILE", blacklist_file):
                with patch.object(Path, "read_text", autospec=True, wraps=Path.read_text) as read_text:
                    first = codes.load_blacklist()
                    second = codes.load_blacklist()

            self.assertEqual(first, {})
            self.assertEqual(second, {})
            self.assertEqual(read_text.call_count, 1)
