from __future__ import annotations

import unittest
from unittest.mock import patch

from botdailygi.services.account_import import _normalize_storage_state
from botdailygi.services.checkin import do_checkin_for_one


class ServiceBehaviorTests(unittest.TestCase):
    def test_normalize_storage_state_requires_cookies_array(self):
        with self.assertRaises(ValueError):
            _normalize_storage_state({})

    def test_normalize_storage_state_filters_invalid_items(self):
        result = _normalize_storage_state(
            {
                "cookies": [
                    {"name": "ltuid_v2", "value": "1"},
                    {"name": "bad", "value": ""},
                    "skip",
                ]
            }
        )
        self.assertEqual(len(result["cookies"]), 1)

    @patch("botdailygi.services.checkin.accounts.list_accounts", return_value=[{"name": "main"}])
    @patch("botdailygi.services.checkin.get_checkin_info", return_value={"data": {"is_sign": True, "total_sign_day": 5}})
    def test_do_checkin_for_one_short_circuits_if_already_signed(self, _get_checkin_info, _list_accounts):
        result = do_checkin_for_one(label="manual", cookies={}, account_name="main", max_retries=1)
        self.assertEqual(result["kind"], "already")

    @patch("botdailygi.services.checkin.accounts.list_accounts", return_value=[{"name": "main"}])
    @patch("botdailygi.services.checkin.wait_checkin_retry")
    @patch("botdailygi.services.checkin.sign_checkin", return_value={"retcode": -1, "message": "server busy"})
    @patch("botdailygi.services.checkin.get_checkin_info", return_value={"data": {"is_sign": False}})
    def test_do_checkin_for_one_retries_and_fails(
        self,
        _get_checkin_info,
        _sign_checkin,
        wait_checkin_retry,
        _list_accounts,
    ):
        result = do_checkin_for_one(label="manual", cookies={}, account_name="main", max_retries=2, retry_wait_min=0)
        self.assertEqual(result["kind"], "failed")
        self.assertEqual(wait_checkin_retry.call_count, 1)
