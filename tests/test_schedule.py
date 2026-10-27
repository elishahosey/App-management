from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from roku_blocker.schedule import Rule


ZONE = ZoneInfo("UTC")


def rule(start="09:00", end="17:00", days=("mon",), enabled=True):
    return Rule.from_dict(
        {
            "name": "test",
            "apps": [{"id": "12", "name": "Netflix"}],
            "days": list(days),
            "start": start,
            "end": end,
            "enabled": enabled,
        }
    )


def at(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=ZONE)


class ScheduleTests(unittest.TestCase):
    def test_same_day_window_is_start_inclusive_end_exclusive(self):
        item = rule()
        self.assertTrue(item.active_at(at(2026, 7, 20, 9)))
        self.assertTrue(item.active_at(at(2026, 7, 20, 16, 59)))
        self.assertFalse(item.active_at(at(2026, 7, 20, 17)))

    def test_overnight_window_uses_starting_day(self):
        item = rule(start="21:00", end="07:00")
        self.assertTrue(item.active_at(at(2026, 7, 20, 23)))
        self.assertTrue(item.active_at(at(2026, 7, 21, 6, 59)))
        self.assertFalse(item.active_at(at(2026, 7, 21, 7)))
        self.assertFalse(item.active_at(at(2026, 7, 22, 6)))

    def test_equal_times_means_all_day_on_selected_day(self):
        item = rule(start="00:00", end="00:00")
        self.assertTrue(item.active_at(at(2026, 7, 20, 13)))
        self.assertFalse(item.active_at(at(2026, 7, 21, 13)))

    def test_matches_id_or_case_insensitive_name(self):
        item = rule()
        moment = at(2026, 7, 20, 10)
        self.assertTrue(item.blocks("12", "Anything", moment))
        self.assertTrue(item.blocks("999", "NETFLIX", moment))
        self.assertFalse(item.blocks("999", "Hulu", moment))

    def test_invalid_day_is_rejected(self):
        with self.assertRaises(ValueError):
            rule(days=("funday",))
