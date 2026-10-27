from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .schedule import Rule, timezone_from_name


_ENV_VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_environment(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: _expand_environment(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_expand_environment(value) for value in data]
    if isinstance(data, str):
        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            value = os.environ.get(name)
            if value is None:
                raise ValueError(
                    f"Environment variable {name!r} referenced in config is not set"
                )
            return value

        return _ENV_VARIABLE.sub(replace, data)
    return data


@dataclass(frozen=True)
class Config:
    platform: str
    address: str
    adb_path: str
    timezone: str
    poll_seconds: float
    action: str
    cooldown_seconds: float
    rules: tuple[Rule, ...]

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        config_path = Path(path)
        load_dotenv(dotenv_path=config_path.with_name(".env"), override=False)
        try:
            data = _expand_environment(
                json.loads(config_path.read_text(encoding="utf-8"))
            )
        except FileNotFoundError as exc:
            raise ValueError(f"Configuration file not found: {config_path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {config_path}: {exc}") from exc

        platform = str(data.get("platform", "roku")).strip().lower()
        if platform not in {"roku", "firetv"}:
            raise ValueError("'platform' must be 'roku' or 'firetv'")
        address = str(data.get("address", data.get("roku_url", ""))).strip().rstrip("/")
        if not address:
            raise ValueError("'address' is required")
        if platform == "roku" and "://" not in address:
            address = f"http://{address}:8060"
        timezone = str(data.get("timezone", "UTC"))
        timezone_from_name(timezone)
        poll_seconds = float(data.get("poll_seconds", 2))
        cooldown_seconds = float(data.get("cooldown_seconds", 5))
        if poll_seconds < 0.5:
            raise ValueError("'poll_seconds' must be at least 0.5")
        if cooldown_seconds < 0:
            raise ValueError("'cooldown_seconds' cannot be negative")
        action = str(data.get("action", "home")).lower()
        if action not in {"home", "poweroff"}:
            raise ValueError("'action' must be 'home' or 'poweroff'")
        rules = tuple(Rule.from_dict(item) for item in data.get("rules", []))
        if not rules:
            raise ValueError("At least one rule is required")
        return cls(
            platform=platform,
            address=address,
            adb_path=str(data.get("adb_path", "adb")),
            timezone=timezone,
            poll_seconds=poll_seconds,
            action=action,
            cooldown_seconds=cooldown_seconds,
            rules=rules,
        )

    @property
    def roku_url(self) -> str:
        """Compatibility property used by version 0.1 integrations."""
        return self.address
