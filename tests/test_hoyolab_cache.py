from __future__ import annotations

import unittest
from unittest.mock import patch

from botdailygi.services import hoyolab


class HoYoLabCacheTests(unittest.TestCase):
    def setUp(self):
        hoyolab.invalidate_account_cache()
        hoyolab.invalidate_api_cache()
        self.cookies = {"ltuid_v2": "1001"}

    @patch("botdailygi.services.hoyolab._game_record_get")
    def test_realtime_notes_uses_short_ttl_cache(self, game_record_get):
        game_record_get.return_value = {"retcode": 0, "data": {"current_resin": 120}}

        first = hoyolab.get_realtime_notes(self.cookies, "8001", "os_asia")
        second = hoyolab.get_realtime_notes(self.cookies, "8001", "os_asia")

        self.assertEqual(first["data"]["current_resin"], 120)
        self.assertEqual(second["data"]["current_resin"], 120)
        game_record_get.assert_called_once()

    @patch("botdailygi.services.hoyolab.HTTP.get")
    def test_checkin_cache_invalidates_after_sign(self, http_get):
        class FakeResponse:
            def __init__(self, payload):
                self._payload = payload

            def json(self):
                return self._payload

        http_get.return_value = FakeResponse({"retcode": 0, "data": {"is_sign": False}})
        first = hoyolab.get_checkin_info(self.cookies)
        second = hoyolab.get_checkin_info(self.cookies)
        self.assertEqual(first["data"]["is_sign"], False)
        self.assertEqual(second["data"]["is_sign"], False)
        self.assertEqual(http_get.call_count, 1)

        with patch("botdailygi.services.hoyolab.HTTP.post") as http_post:
            http_post.return_value = FakeResponse({"retcode": 0, "message": "ok"})
            hoyolab.sign_checkin(self.cookies)

        http_get.return_value = FakeResponse({"retcode": 0, "data": {"is_sign": True}})
        third = hoyolab.get_checkin_info(self.cookies)
        self.assertEqual(third["data"]["is_sign"], True)
        self.assertEqual(http_get.call_count, 2)
