from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from botdailygi.commands.accounts import cmd_addaccount, cmd_removeaccount, handle_cookie_document


class AccountsCommandTests(unittest.TestCase):
    @patch("botdailygi.commands.accounts.send_text")
    def test_cmd_addaccount_requires_name(self, send_text):
        cmd_addaccount(123, "")
        send_text.assert_called_once()

    @patch("botdailygi.commands.accounts.ProgressMessage")
    @patch("botdailygi.commands.accounts.start_pending_import")
    @patch("botdailygi.commands.accounts.accounts.get_cookie_path_for_slug")
    @patch("botdailygi.commands.accounts.accounts.slugify_account_name", return_value="main")
    @patch("botdailygi.commands.accounts.accounts.get_account_entry", return_value=None)
    def test_cmd_addaccount_opens_import_session(
        self,
        _get_account_entry,
        _slugify,
        get_cookie_path_for_slug,
        start_pending_import,
        progress_cls,
    ):
        get_cookie_path_for_slug.return_value.exists.return_value = False
        progress = MagicMock(message_id=10)
        progress_cls.start.return_value = progress
        start_pending_import.return_value = MagicMock(cookie_file="main.json")

        cmd_addaccount(123, "Main")

        progress.done.assert_called_once()

    @patch("botdailygi.commands.accounts.send_text")
    @patch("botdailygi.commands.accounts.accounts.remove_account_entry", return_value=(False, "not found"))
    def test_cmd_removeaccount_reports_error(self, _remove_account_entry, send_text):
        cmd_removeaccount(123, "Main")
        send_text.assert_called_once()

    @patch("botdailygi.commands.accounts.send_text")
    def test_handle_cookie_document_requires_pending_session(self, send_text):
        with patch("botdailygi.commands.accounts.get_pending_import", return_value=None):
            handle_cookie_document(123, {})
        send_text.assert_called_once()

    @patch("botdailygi.commands.accounts.ProgressMessage")
    @patch("botdailygi.commands.accounts.get_pending_import")
    def test_handle_cookie_document_rejects_non_json(self, get_pending_import, progress_cls):
        pending = MagicMock(progress_message_id=10, account_name="Main")
        get_pending_import.return_value = pending
        progress = MagicMock()
        progress_cls.return_value = progress

        handle_cookie_document(123, {"file_name": "cookie.txt", "file_size": 10})

        progress.fail.assert_called_once()

    @patch("botdailygi.commands.accounts.ProgressMessage")
    @patch("botdailygi.commands.accounts.get_pending_import")
    def test_handle_cookie_document_rejects_missing_file_id(self, get_pending_import, progress_cls):
        pending = MagicMock(progress_message_id=10, account_name="Main")
        get_pending_import.return_value = pending
        progress = MagicMock()
        progress_cls.return_value = progress

        handle_cookie_document(123, {"file_name": "cookie.json", "file_size": 10})

        progress.fail.assert_called_once()
