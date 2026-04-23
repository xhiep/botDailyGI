from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from botdailygi.services import accounts, resin_config


class RuntimeCacheTests(unittest.TestCase):
    def test_read_accounts_reuses_empty_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            accounts_file = Path(temp_dir) / "accounts.json"
            accounts_file.write_text("[]", encoding="utf-8")
            accounts.invalidate_account_storage_cache()

            with patch("botdailygi.services.accounts.ACCOUNTS_FILE", accounts_file):
                with patch.object(Path, "read_text", autospec=True, wraps=Path.read_text) as read_text:
                    first = accounts.read_accounts()
                    second = accounts.read_accounts()

            self.assertEqual(first, [])
            self.assertEqual(second, [])
            self.assertEqual(read_text.call_count, 1)

    def test_load_resin_config_reuses_empty_schema_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "resin_notify.json"
            config_file.write_text("{}", encoding="utf-8")
            resin_config._cache = {}
            resin_config._cache_mtime = 0.0

            with patch("botdailygi.services.resin_config.RESIN_NOTIFY_FILE", config_file):
                with patch.object(Path, "read_text", autospec=True, wraps=Path.read_text) as read_text:
                    first = resin_config.load_resin_config()
                    second = resin_config.load_resin_config()

            self.assertEqual(first["default"]["threshold"], 200)
            self.assertEqual(second["default"]["threshold"], 200)
            self.assertEqual(read_text.call_count, 1)
