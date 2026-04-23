from __future__ import annotations

import unittest
from unittest.mock import patch

from botdailygi.clients.telegram import edit_text


class TelegramClientTests(unittest.TestCase):
    @patch("botdailygi.clients.telegram.HTTP.post")
    def test_edit_text_treats_not_modified_as_success(self, http_post):
        class FakeResponse:
            status_code = 400

            def json(self):
                return {"ok": False, "error_code": 400, "description": "Bad Request: message is not modified"}

        http_post.return_value = FakeResponse()

        ok = edit_text(123, 456, "same text")

        self.assertTrue(ok)
        http_post.assert_called_once()
