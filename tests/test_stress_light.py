from __future__ import annotations

import tempfile
import time
import unittest
from unittest.mock import patch

from botdailygi.services import accounts, codes, resin_config


class LightStressTests(unittest.TestCase):
    def test_hot_paths_are_stable_under_repeated_cached_calls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = accounts.Path(temp_dir)
            accounts_file = root / "accounts.json"
            resin_file = root / "resin_notify.json"
            blacklist_file = root / "codes_blacklist.txt"
            accounts_file.write_text("[]", encoding="utf-8")
            resin_file.write_text("{}", encoding="utf-8")
            blacklist_file.write_text("", encoding="utf-8")

            with patch("botdailygi.services.accounts.ACCOUNTS_FILE", accounts_file), patch(
                "botdailygi.services.resin_config.RESIN_NOTIFY_FILE", resin_file
            ), patch("botdailygi.services.codes.CODES_BLACKLIST_FILE", blacklist_file):
                accounts.invalidate_account_storage_cache()
                codes.invalidate_blacklist_cache()
                resin_config._cache = {}
                resin_config._cache_mtime = 0.0

                started = time.perf_counter()
                for _ in range(1000):
                    accounts.read_accounts()
                    resin_config.load_resin_config()
                    codes.load_blacklist()
                elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 1.0)
