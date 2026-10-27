import unittest
from unittest.mock import patch

from roku_blocker.firetv import FireTVClient


class Result:
    returncode = 0
    stderr = ""

    def __init__(self, stdout):
        self.stdout = stdout


class FireTVTests(unittest.TestCase):
    @patch("roku_blocker.firetv.shutil.which", return_value="adb")
    @patch("roku_blocker.firetv.subprocess.run")
    def test_reads_foreground_package(self, run, _which):
        run.side_effect = [
            Result("connected to 192.168.1.4:5555"),
            Result(
                "mResumedActivity: ActivityRecord{123 u0 "
                "com.netflix.ninja/.MainActivity t12}"
            ),
        ]
        client = FireTVClient("192.168.1.4")
        app = client.active_app()
        self.assertEqual(app.app_id, "com.netflix.ninja")

    @patch("roku_blocker.firetv.shutil.which", return_value="adb")
    @patch("roku_blocker.firetv.subprocess.run")
    def test_lists_third_party_packages(self, run, _which):
        run.side_effect = [
            Result("already connected"),
            Result("package:com.netflix.ninja\npackage:tv.twitch.android.app\n"),
        ]
        client = FireTVClient("192.168.1.4")
        self.assertEqual(
            [app.app_id for app in client.apps()],
            ["com.netflix.ninja", "tv.twitch.android.app"],
        )
