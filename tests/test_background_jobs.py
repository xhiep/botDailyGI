from __future__ import annotations

import unittest

from botdailygi.background.jobs import _next_resin_check_seconds


class BackgroundJobTests(unittest.TestCase):
    def test_next_resin_check_uses_eta_before_threshold(self):
        delay = _next_resin_check_seconds(current=100, maximum=200, eta_seconds=3600, threshold=120, threshold_critical=128)
        self.assertEqual(delay, 3600)

    def test_next_resin_check_has_minimum_interval(self):
        delay = _next_resin_check_seconds(current=119, maximum=200, eta_seconds=10, threshold=120, threshold_critical=128)
        self.assertEqual(delay, 60)

    def test_next_resin_check_waits_longer_after_threshold(self):
        delay = _next_resin_check_seconds(current=121, maximum=200, eta_seconds=0, threshold=120, threshold_critical=128)
        self.assertGreaterEqual(delay, 300)
