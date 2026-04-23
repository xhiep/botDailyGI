from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from botdailygi.commands.resin import cmd_resin, cmd_resinnotify


class ResinCommandTests(unittest.TestCase):
    @patch("botdailygi.commands.resin.send_text")
    @patch("botdailygi.commands.resin.active_accounts", return_value=[])
    def test_cmd_resin_requires_account(self, _active_accounts, send_text):
        cmd_resin(123)
        send_text.assert_called_once()

    @patch("botdailygi.commands.resin.ProgressMessage")
    @patch("botdailygi.commands.resin.parallel_account_map", return_value=["block-1", "block-2"])
    @patch("botdailygi.commands.resin.active_accounts", return_value=[({"name": "a"}, {}), ({"name": "b"}, {})])
    def test_cmd_resin_renders_blocks(self, _active_accounts, _parallel_map, progress_cls):
        progress = MagicMock()
        progress_cls.start.return_value = progress
        cmd_resin(123)
        progress.done.assert_called_once()

    @patch("botdailygi.commands.resin.send_text")
    @patch("botdailygi.commands.resin.active_accounts", return_value=[])
    @patch("botdailygi.commands.resin.load_resin_config", return_value={"default": {"enabled": True, "threshold": 200}, "accounts": {}})
    def test_cmd_resinnotify_status_requires_account(self, _load_config, _active_accounts, send_text):
        cmd_resinnotify(123, "")
        send_text.assert_called_once()

    @patch("botdailygi.commands.resin.resin_wake_event")
    @patch("botdailygi.commands.resin.save_resin_config")
    @patch("botdailygi.commands.resin.send_text")
    @patch("botdailygi.commands.resin.check_change_cooldown", return_value=0)
    @patch("botdailygi.commands.resin.mark_change")
    @patch("botdailygi.commands.resin.load_resin_config", return_value={"default": {"enabled": True, "threshold": 200}, "accounts": {}})
    @patch("botdailygi.commands.resin.active_accounts", return_value=[({"name": "main"}, {"ltuid_v2": "1"})])
    def test_cmd_resinnotify_sets_single_threshold(
        self,
        _active_accounts,
        _load_config,
        mark_change,
        _cooldown,
        send_text,
        save_resin_config,
        resin_wake_event,
    ):
        cmd_resinnotify(123, "160")
        mark_change.assert_called_once_with(123)
        save_resin_config.assert_called_once()
        resin_wake_event.set.assert_called_once()
        send_text.assert_called()

    @patch("botdailygi.commands.resin.send_text")
    @patch("botdailygi.commands.resin.check_change_cooldown", return_value=0)
    @patch("botdailygi.commands.resin.mark_change")
    @patch("botdailygi.commands.resin.load_resin_config", return_value={"default": {"enabled": True, "threshold": 200}, "accounts": {}})
    @patch("botdailygi.commands.resin.active_accounts", return_value=[({"name": "main"}, {})])
    def test_cmd_resinnotify_rejects_missing_target(
        self,
        _active_accounts,
        _load_config,
        _mark_change,
        _cooldown,
        send_text,
    ):
        cmd_resinnotify(123, "alt on")
        send_text.assert_called_once()
