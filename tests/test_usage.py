import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import usage


class UsageMonitorTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.usage_path_patch = patch.object(
            usage, "USAGE_FILE", Path(self.temp_directory.name) / "usage.json"
        )
        self.usage_path_patch.start()

    def tearDown(self):
        self.usage_path_patch.stop()
        self.temp_directory.cleanup()

    def test_persists_deepseek_token_fields_and_summarizes_specified_month(self):
        response = SimpleNamespace(
            usage=SimpleNamespace(
                prompt_tokens=4000,
                completion_tokens=2000,
                total_tokens=6000,
                prompt_cache_hit_tokens=500,
                prompt_cache_miss_tokens=3500,
            )
        )
        usage.record_response_usage(response)

        persisted = json.loads(usage.USAGE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["input_tokens"], 4000)
        self.assertEqual(persisted[0]["output_tokens"], 2000)
        self.assertEqual(persisted[0]["total_tokens"], 6000)
        self.assertEqual(persisted[0]["cache_hit_tokens"], 500)
        self.assertEqual(persisted[0]["cache_miss_tokens"], 3500)
        self.assertTrue(persisted[0]["timestamp"])

        # Freeze the persisted record to a known month so this test is deterministic.
        persisted[0]["timestamp"] = "2026-09-01T12:00:00+00:00"
        usage.USAGE_FILE.write_text(
            json.dumps(persisted),
            encoding="utf-8",
        )

        # Reading the persisted file again models a Linkzen restart.
        summary = usage.summarize_usage(
            "UTC", now=datetime(2026, 9, 10, 12, tzinfo=timezone.utc)
        )
        self.assertEqual(summary["month_tokens"], 6000)
        self.assertEqual(summary["daily_average_tokens"], 600)

    def test_daily_average_uses_days_elapsed_and_month_rolls_over(self):
        usage.USAGE_FILE.write_text(
            json.dumps([
                {"timestamp": "2026-09-01T12:00:00+00:00", "total_tokens": 900000},
                {"timestamp": "2026-08-31T23:59:00+00:00", "total_tokens": 700000},
            ]),
            encoding="utf-8",
        )

        september = usage.summarize_usage(
            "UTC", now=datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
        )
        october = usage.summarize_usage(
            "UTC", now=datetime(2026, 10, 1, 0, tzinfo=timezone.utc)
        )

        self.assertEqual(september["month_tokens"], 900000)
        self.assertEqual(september["daily_average_tokens"], 100000)
        self.assertFalse(september["monthly_warning"])
        self.assertEqual(october["month_tokens"], 0)
        self.assertEqual(october["daily_average_tokens"], 0)

    def test_monthly_warning_starts_at_one_million_tokens(self):
        usage.USAGE_FILE.write_text(
            json.dumps([
                {"timestamp": "2026-09-01T12:00:00+00:00", "total_tokens": 600000},
                {"timestamp": "2026-09-02T12:00:00+00:00", "total_tokens": 400000},
            ]),
            encoding="utf-8",
        )
        summary = usage.summarize_usage(
            "UTC", now=datetime(2026, 9, 2, 12, tzinfo=timezone.utc)
        )
        self.assertEqual(summary["month_tokens"], 1_000_000)
        self.assertTrue(summary["monthly_warning"])

    def test_peak_status_tracks_kabul_schedule_boundaries(self):
        before_peak = usage.summarize_usage(
            "UTC", now=datetime(2026, 9, 1, 0, 59, tzinfo=timezone.utc)
        )
        peak = usage.summarize_usage(
            "UTC", now=datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc)
        )
        after_peak = usage.summarize_usage(
            "UTC", now=datetime(2026, 9, 1, 4, 0, tzinfo=timezone.utc)
        )
        weekend = usage.summarize_usage(
            "UTC", now=datetime(2026, 9, 5, 1, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(before_peak["peak_status"], "Off-peak")
        self.assertEqual(peak["peak_status"], "Peak")
        self.assertEqual(after_peak["peak_status"], "Off-peak")
        self.assertEqual(weekend["peak_status"], "Off-peak")

    def test_summary_uses_users_local_month_and_clock(self):
        usage.USAGE_FILE.write_text(
            json.dumps([
                {"timestamp": "2026-09-01T10:30:00+00:00", "total_tokens": 42000}
            ]),
            encoding="utf-8",
        )
        summary = usage.summarize_usage(
            "America/Los_Angeles",
            now=datetime(2026, 9, 1, 10, 58, tzinfo=timezone.utc),
        )
        self.assertEqual(summary["month_tokens"], 42000)
        self.assertEqual(summary["local_time"], "3:28 PM")
        self.assertEqual(summary["peak_status"], "Off-peak")


if __name__ == "__main__":
    unittest.main()