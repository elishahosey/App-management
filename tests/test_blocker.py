from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from roku_blocker.blocker import AppBlocker
from roku_blocker.config import Config
from roku_blocker.models import AppInfo
from roku_blocker.schedule import Rule


class FakeClient:
    def __init__(self, app):
        self.app = app
        self.keys = []

    def active_app(self):
        return self.app

    def go_home(self):
        self.keys.append("Home")

    def power_off(self):
        self.keys.append("PowerOff")


def make_config(action="home"):
    return Config(
        platform="roku",
        address="http://roku:8060",
        adb_path="adb",
        timezone="UTC",
        poll_seconds=2,
        cooldown_seconds=5,
        action=action,
        rules=(
            Rule.from_dict(
                {
                    "name": "blocked",
                    "apps": [{"id": "12"}],
                    "days": ["mon"],
                    "start": "09:00",
                    "end": "17:00",
                }
            ),
        ),
    )


class BlockerTests(unittest.TestCase):
    def test_blocked_app_sends_home(self):
        client = FakeClient(AppInfo("12", "Netflix"))
        blocker = AppBlocker(make_config(), client=client, clock=lambda: 10)
        blocked = blocker.check_once(
            datetime(2026, 7, 20, 10, tzinfo=ZoneInfo("UTC"))
        )
        self.assertTrue(blocked)
        self.assertEqual(client.keys, ["Home"])

    def test_allowed_app_does_nothing(self):
        client = FakeClient(AppInfo("837", "YouTube"))
        blocker = AppBlocker(make_config(), client=client, clock=lambda: 10)
        blocked = blocker.check_once(
            datetime(2026, 7, 20, 10, tzinfo=ZoneInfo("UTC"))
        )
        self.assertFalse(blocked)
        self.assertEqual(client.keys, [])

    def test_dry_run_does_not_send_key(self):
        client = FakeClient(AppInfo("12", "Netflix"))
        blocker = AppBlocker(make_config(), client=client, clock=lambda: 10)
        self.assertTrue(
            blocker.check_once(
                datetime(2026, 7, 20, 10, tzinfo=ZoneInfo("UTC")), enforce=False
            )
        )
        self.assertEqual(client.keys, [])
