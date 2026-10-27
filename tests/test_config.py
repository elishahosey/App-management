import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dotenv import dotenv_values

from roku_blocker.config import Config


class ConfigTests(unittest.TestCase):
    def write_config(self, directory: Path, address="${TV_BLOCKER_TEST_ADDRESS}"):
        config = {
            "platform": "firetv",
            "address": address,
            "timezone": "UTC",
            "rules": [
                {
                    "name": "${TV_BLOCKER_TEST_RULE}",
                    "apps": [{"id": "${TV_BLOCKER_TEST_APP_ID}"}],
                    "days": ["mon"],
                    "start": "09:00",
                    "end": "17:00",
                }
            ],
        }
        config_path = directory / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        return config_path

    def test_expands_variables_from_adjacent_env_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            self.write_config(directory)
            (directory / ".env").write_text(
                "TV_BLOCKER_TEST_ADDRESS=192.0.2.1:5555\n"
                "TV_BLOCKER_TEST_RULE=Example rule\n"
                "TV_BLOCKER_TEST_APP_ID=com.example.app\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                config = Config.load(directory / "config.json")

        self.assertEqual(config.address, "192.0.2.1:5555")
        self.assertEqual(config.rules[0].name, "Example rule")
        self.assertEqual(config.rules[0].app_ids, {"com.example.app"})

    def test_process_environment_overrides_env_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            self.write_config(directory)
            (directory / ".env").write_text(
                "TV_BLOCKER_TEST_ADDRESS=192.0.2.1:5555\n"
                "TV_BLOCKER_TEST_RULE=Example rule\n"
                "TV_BLOCKER_TEST_APP_ID=com.example.app\n",
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "TV_BLOCKER_TEST_ADDRESS": "192.0.2.2:5555",
                    "TV_BLOCKER_TEST_RULE": "Example rule",
                    "TV_BLOCKER_TEST_APP_ID": "com.example.app",
                },
                clear=True,
            ):
                config = Config.load(directory / "config.json")

        self.assertEqual(config.address, "192.0.2.2:5555")

    def test_missing_variable_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            config_path = self.write_config(directory)

            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(
                    ValueError, "TV_BLOCKER_TEST_ADDRESS.*not set"
                ):
                    Config.load(config_path)

    def test_example_config_loads_with_example_environment(self):
        repository = Path(__file__).parents[1]
        environment = {
            key: value
            for key, value in dotenv_values(repository / ".env.example").items()
            if value is not None
        }

        with patch.dict(os.environ, environment, clear=True):
            config = Config.load(repository / "config.example.json")

        self.assertEqual(config.address, "192.0.2.10:5555")
        self.assertEqual(config.rules[0].name, "Example app rule")


if __name__ == "__main__":
    unittest.main()
