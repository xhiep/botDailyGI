from __future__ import annotations

import unittest
from unittest.mock import patch

from botdailygi.renderers.text import divider, meter_bar
from botdailygi.services.progress import ProgressMessage


class RendererProgressTests(unittest.TestCase):
    def test_divider_and_meter_bar(self):
        self.assertEqual(divider(5), "─────")
        self.assertEqual(meter_bar(50, 100, width=10), "█████░░░░░")

    @patch("botdailygi.services.progress.send_text", return_value=1)
    @patch("botdailygi.services.progress.send_chat_action", return_value=True)
    def test_progress_start_adds_frame(self, _action, send_text):
        ProgressMessage.start(123, "Loading")
        sent = send_text.call_args.args[1]
        self.assertIn("Loading", sent)
        self.assertIn("Đang xử lý", sent)

    @patch("botdailygi.services.progress.send_text", return_value=1)
    @patch("botdailygi.services.progress.edit_text", return_value=False)
    @patch("botdailygi.services.progress.send_chat_action", return_value=True)
    def test_progress_done_adds_completion_header(self, _action, _edit_text, send_text):
        progress = ProgressMessage(chat_id=123, message_id=1)
        progress.done("Finished")
        sent = send_text.call_args.args[1]
        self.assertTrue(sent.startswith("✓ Hoàn tất"))
