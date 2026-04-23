from __future__ import annotations

import unittest
from unittest.mock import patch

from botdailygi.core.dispatcher import handle_callback, handle_text


class DispatcherTests(unittest.TestCase):
    @patch("botdailygi.core.dispatcher.authorized", return_value=False)
    @patch("botdailygi.core.dispatcher.send_text")
    def test_handle_text_rejects_unauthorized(self, send_text, _authorized):
        handle_text(123, "/status")
        send_text.assert_called_once()

    @patch("botdailygi.core.dispatcher.authorized", return_value=True)
    @patch("botdailygi.core.dispatcher.send_text")
    def test_handle_text_rejects_unknown_command(self, send_text, _authorized):
        handle_text(123, "/missing")
        send_text.assert_called_once()

    @patch("botdailygi.core.dispatcher.authorized", return_value=True)
    @patch("botdailygi.core.dispatcher.invalidate_status_cache")
    @patch("botdailygi.core.dispatcher.cmd_help")
    @patch("botdailygi.core.dispatcher.answer_callback")
    @patch("botdailygi.core.dispatcher.set_lang")
    @patch("botdailygi.core.dispatcher.mark_change")
    @patch("botdailygi.core.dispatcher.check_change_cooldown", return_value=0)
    def test_handle_callback_changes_language(
        self,
        _cooldown,
        mark_change,
        set_lang,
        answer_callback,
        cmd_help,
        invalidate_status_cache,
        _authorized,
    ):
        handle_callback("cb1", 123, "lang_en")
        mark_change.assert_called_once_with(123)
        set_lang.assert_called_once_with(123, "en")
        invalidate_status_cache.assert_called_once()
        answer_callback.assert_called()
        cmd_help.assert_called_once_with(123)
