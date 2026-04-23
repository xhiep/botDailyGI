from __future__ import annotations

import types
import unittest
from unittest.mock import MagicMock, patch

from botdailygi.commands.profile import cmd_abyss, cmd_uid
from botdailygi.commands.schedule import cmd_livestream
from botdailygi.commands.status import cmd_status


class ScheduleProfileStatusTests(unittest.TestCase):
    @patch("botdailygi.commands.schedule.send_text")
    @patch("botdailygi.commands.schedule.get_current_version", return_value="6.5")
    @patch("botdailygi.commands.schedule.get_versions", side_effect=RuntimeError("boom"))
    def test_cmd_livestream_uses_fallback_versions(self, _get_versions, _current_version, send_text):
        cmd_livestream(123)
        send_text.assert_called_once()

    @patch("botdailygi.commands.profile.send_text")
    @patch("botdailygi.commands.profile.active_accounts", return_value=[])
    def test_cmd_uid_requires_account(self, _active_accounts, send_text):
        cmd_uid(123)
        send_text.assert_called_once()

    @patch("botdailygi.commands.profile.ProgressMessage")
    @patch("botdailygi.commands.profile.parallel_account_map", return_value=[("text", None)])
    @patch("botdailygi.commands.profile.active_accounts", return_value=[({"name": "main"}, {})])
    def test_cmd_abyss_text_fallback(self, _active_accounts, _parallel_map, progress_cls):
        progress = MagicMock()
        progress_cls.start.return_value = progress
        cmd_abyss(123)
        progress.done.assert_called_once()

    @patch("botdailygi.commands.status.ProgressMessage")
    @patch("botdailygi.commands.status.active_accounts", return_value=[])
    @patch("botdailygi.commands.status.threading.enumerate", return_value=[])
    def test_cmd_status_without_accounts(self, _enumerate, _active_accounts, progress_cls):
        progress = MagicMock()
        progress_cls.start.return_value = progress
        with patch("botdailygi.commands.status.command_executor", types.SimpleNamespace(_work_queue=types.SimpleNamespace(qsize=lambda: 0))):
            cmd_status(123)
        progress.done.assert_called_once()
