from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from botdailygi.commands.checkin import cmd_checkin


class CheckinCommandTests(unittest.TestCase):
    @patch("botdailygi.commands.checkin.send_text")
    @patch("botdailygi.commands.checkin.manual_checkin_lock")
    def test_cmd_checkin_rejects_when_busy(self, manual_checkin_lock, send_text):
        manual_checkin_lock.acquire.return_value = False
        cmd_checkin(123)
        send_text.assert_called_once()

    @patch("botdailygi.commands.checkin.ProgressMessage")
    @patch("botdailygi.commands.checkin.do_checkin_for_all", return_value=[{"kind": "success", "label": "manual", "ok": True}])
    @patch("botdailygi.commands.checkin.invalidate_api_cache")
    @patch("botdailygi.commands.checkin.invalidate_status_cache")
    @patch("botdailygi.commands.checkin.manual_checkin_lock")
    def test_cmd_checkin_runs_and_releases_lock(
        self,
        manual_checkin_lock,
        _invalidate_status_cache,
        _invalidate_api_cache,
        _do_checkin_for_all,
        progress_cls,
    ):
        manual_checkin_lock.acquire.return_value = True
        progress = MagicMock()
        progress_cls.start.return_value = progress

        cmd_checkin(123)

        progress.done.assert_called_once()
        manual_checkin_lock.release.assert_called_once()

    @patch("botdailygi.commands.checkin.ProgressMessage")
    @patch("botdailygi.commands.checkin.do_checkin_for_all", side_effect=RuntimeError("boom"))
    @patch("botdailygi.commands.checkin.manual_checkin_lock")
    def test_cmd_checkin_reports_failure(self, manual_checkin_lock, _do_checkin_for_all, progress_cls):
        manual_checkin_lock.acquire.return_value = True
        progress = MagicMock()
        progress_cls.start.return_value = progress

        cmd_checkin(123)

        progress.fail.assert_called_once()
        manual_checkin_lock.release.assert_called_once()
