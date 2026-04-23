from __future__ import annotations

import unittest
from unittest.mock import patch

from botdailygi.commands.system import cmd_lang, cmd_start


class SystemCommandTests(unittest.TestCase):
    @patch("botdailygi.commands.system.send_buttons")
    def test_cmd_start_sends_language_buttons(self, send_buttons):
        cmd_start(123)
        send_buttons.assert_called_once()

    @patch("botdailygi.commands.system.cmd_help")
    @patch("botdailygi.commands.system.send_text")
    @patch("botdailygi.commands.system.invalidate_status_cache")
    @patch("botdailygi.commands.system.set_lang")
    @patch("botdailygi.commands.system.mark_change")
    @patch("botdailygi.commands.system.check_change_cooldown", return_value=0)
    def test_cmd_lang_switches_language(
        self,
        _cooldown,
        mark_change,
        set_lang,
        invalidate_status_cache,
        send_text,
        cmd_help,
    ):
        cmd_lang(123, "en")
        mark_change.assert_called_once_with(123)
        set_lang.assert_called_once_with(123, "en")
        invalidate_status_cache.assert_called_once()
        send_text.assert_called()
        cmd_help.assert_called_once_with(123)

    @patch("botdailygi.commands.system.send_text")
    @patch("botdailygi.commands.system.check_change_cooldown", return_value=1.0)
    def test_cmd_lang_honors_cooldown(self, _cooldown, send_text):
        cmd_lang(123, "vi")
        send_text.assert_called_once()

    @patch("botdailygi.commands.system.send_buttons")
    @patch("botdailygi.commands.system.get_lang", return_value="vi")
    def test_cmd_lang_without_arg_shows_buttons(self, _get_lang, send_buttons):
        cmd_lang(123, "")
        send_buttons.assert_called_once()
