from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from botdailygi.commands.advanced import cmd_alias, cmd_default, cmd_history
from botdailygi.services.history import append_history, recent_history


class AdvancedFeatureTests(unittest.TestCase):
    def test_history_append_and_recent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history_file = Path(temp_dir) / "history.jsonl"
            with patch("botdailygi.services.history.HISTORY_FILE", history_file):
                append_history("resin", "main", {"current": 120})
                append_history("checkin", "main", {"checked": True})
                rows = recent_history(account="main", limit=5)
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0]["kind"], "checkin")

    def test_backup_archive_contains_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "accounts.json").write_text("[]", encoding="utf-8")
            (root / "resin_notify.json").write_text("{}", encoding="utf-8")
            (root / "user_langs.json").write_text("{}", encoding="utf-8")
            (root / "user_settings.json").write_text("{}", encoding="utf-8")
            (root / "codes_blacklist.txt").write_text("", encoding="utf-8")
            (root / "history.jsonl").write_text("", encoding="utf-8")
            cookies = root / "cookies"
            cookies.mkdir()
            (cookies / "main.json").write_text("{}", encoding="utf-8")
            with patch("botdailygi.services.backup.ACCOUNTS_FILE", root / "accounts.json"), patch(
                "botdailygi.services.backup.RESIN_NOTIFY_FILE", root / "resin_notify.json"
            ), patch("botdailygi.services.backup.USER_LANGS_FILE", root / "user_langs.json"), patch(
                "botdailygi.services.backup.USER_SETTINGS_FILE", root / "user_settings.json"
            ), patch(
                "botdailygi.services.backup.CODES_BLACKLIST_FILE", root / "codes_blacklist.txt"
            ), patch(
                "botdailygi.services.backup.HISTORY_FILE", root / "history.jsonl"
            ), patch(
                "botdailygi.services.backup.COOKIES_DIR", cookies
            ):
                from botdailygi.services.backup import build_backup_archive

                archive = build_backup_archive()
                self.assertIn(b"backup_manifest.json", archive)

    @patch("botdailygi.commands.advanced.send_text")
    @patch("botdailygi.commands.advanced.accounts.get_account_entry", return_value={"name": "Main"})
    @patch("botdailygi.commands.advanced.set_default_account")
    def test_cmd_default_sets_account(self, set_default_account, _get_account_entry, send_text):
        cmd_default(123, "Main")
        set_default_account.assert_called_once_with("Main")
        send_text.assert_called_once()

    @patch("botdailygi.commands.advanced.send_text")
    @patch("botdailygi.commands.advanced.remove_alias")
    def test_cmd_alias_removes_alias(self, remove_alias, send_text):
        cmd_alias(123, "remove alt")
        remove_alias.assert_called_once_with("alt")
        send_text.assert_called_once()

    @patch("botdailygi.commands.advanced.send_text")
    @patch("botdailygi.commands.advanced.snapshot_history_state", return_value={"count": 1})
    @patch(
        "botdailygi.commands.advanced.recent_history",
        return_value=[{"ts": "2026-04-27T01:00:00+00:00", "kind": "resin", "account": "main", "payload": {"current": 120, "max": 200}}],
    )
    def test_cmd_history_formats_resin_summary(self, _recent_history, _snapshot, send_text):
        cmd_history(123, "main 1")
        sent = send_text.call_args.args[1]
        self.assertIn("120/200", sent)
