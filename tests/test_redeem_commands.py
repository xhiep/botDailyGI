from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from botdailygi.commands.redeem import cmd_clearblacklist, cmd_redeem, cmd_redeemall


class RedeemCommandTests(unittest.TestCase):
    @patch("botdailygi.commands.redeem.send_text")
    def test_cmd_redeem_requires_code(self, send_text):
        cmd_redeem(123, "")
        send_text.assert_called_once()

    @patch("botdailygi.commands.redeem.send_text")
    @patch("botdailygi.commands.redeem.load_blacklist", return_value={"ABC": "expired"})
    def test_cmd_redeem_rejects_blacklisted_code(self, _load_blacklist, send_text):
        cmd_redeem(123, "abc")
        send_text.assert_called_once()

    @patch("botdailygi.commands.redeem.send_text")
    @patch("botdailygi.commands.redeem.load_blacklist", return_value={})
    @patch("botdailygi.commands.redeem.accounts.all_account_cookies", return_value=[])
    def test_cmd_redeem_requires_accounts(self, _all_account_cookies, _load_blacklist, send_text):
        cmd_redeem(123, "ABC")
        send_text.assert_called_once()

    @patch("botdailygi.commands.redeem.send_text")
    @patch("botdailygi.commands.redeem.redeem_lock")
    @patch("botdailygi.commands.redeem.load_blacklist", return_value={})
    @patch("botdailygi.commands.redeem.accounts.all_account_cookies", return_value=[({"name": "main"}, {})])
    def test_cmd_redeem_rejects_when_busy(self, _all_account_cookies, _load_blacklist, redeem_lock, send_text):
        redeem_lock.acquire.return_value = False
        cmd_redeem(123, "ABC")
        send_text.assert_called_once()

    @patch("botdailygi.commands.redeem.ProgressMessage")
    @patch("botdailygi.commands.redeem._parallel_account_map", return_value=["ok"])
    @patch("botdailygi.commands.redeem.get_lang", return_value="vi")
    @patch("botdailygi.commands.redeem.redeem_lock")
    @patch("botdailygi.commands.redeem.load_blacklist", return_value={})
    @patch("botdailygi.commands.redeem.accounts.all_account_cookies", return_value=[({"name": "main"}, {})])
    def test_cmd_redeem_runs(
        self,
        _all_account_cookies,
        _load_blacklist,
        redeem_lock,
        _get_lang,
        _parallel_account_map,
        progress_cls,
    ):
        redeem_lock.acquire.return_value = True
        progress = MagicMock()
        progress_cls.start.return_value = progress
        cmd_redeem(123, "ABC")
        progress.done.assert_called_once()
        redeem_lock.release.assert_called_once()

    @patch("botdailygi.commands.redeem.send_text")
    @patch("botdailygi.commands.redeem.redeem_lock")
    @patch("botdailygi.commands.redeem.load_codes_from_file", return_value=[])
    def test_cmd_redeemall_requires_codes(self, _load_codes, redeem_lock, send_text):
        redeem_lock.acquire.return_value = True
        cmd_redeemall(123)
        send_text.assert_called_once()
        redeem_lock.release.assert_called_once()

    @patch("botdailygi.commands.redeem.send_text")
    @patch("botdailygi.commands.redeem.load_blacklist", return_value={})
    def test_cmd_clearblacklist_handles_empty(self, _load_blacklist, send_text):
        cmd_clearblacklist(123)
        send_text.assert_called_once()
