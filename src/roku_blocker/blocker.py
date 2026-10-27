from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Callable

from .config import Config
from .client import TVClient, TVError
from .firetv import FireTVClient
from .models import AppInfo
from .roku import RokuClient
from .schedule import timezone_from_name


class AppBlocker:
    def __init__(
        self,
        config: Config,
        client: TVClient | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.config = config
        self.client = client or make_client(config)
        self.clock = clock
        self.timezone = timezone_from_name(config.timezone)
        self.last_action_at = float("-inf")
        self.log = logging.getLogger("roku_blocker")

    def matching_rules(self, app: AppInfo, moment: datetime) -> list[str]:
        return [
            rule.name
            for rule in self.config.rules
            if rule.blocks(app.app_id, app.name, moment)
        ]

    def check_once(self, moment: datetime | None = None, enforce: bool = True) -> bool:
        moment = moment or datetime.now(self.timezone)
        app = self.client.active_app()
        matches = self.matching_rules(app, moment)
        if not matches:
            self.log.debug("Allowed: %s (%s)", app.name or "unknown", app.app_id)
            return False
        self.log.warning(
            "Blocked app detected: %s (%s); matching rules: %s",
            app.name,
            app.app_id,
            ", ".join(matches),
        )
        if enforce and self.clock() - self.last_action_at >= self.config.cooldown_seconds:
            key = "Home" if self.config.action == "home" else "PowerOff"
            if self.config.action == "home":
                self.client.go_home()
            else:
                self.client.power_off()
            self.last_action_at = self.clock()
            self.log.warning("Enforced block with TV action: %s", key)
        return True

    def run_forever(self) -> None:
        self.log.info("Monitoring %s every %.1f seconds", self.config.address, self.config.poll_seconds)
        failures = 0
        while True:
            try:
                self.check_once()
                failures = 0
                delay = self.config.poll_seconds
            except TVError as exc:
                failures += 1
                delay = min(60.0, self.config.poll_seconds * (2 ** min(failures, 5)))
                self.log.error("%s; retrying in %.1f seconds", exc, delay)
            time.sleep(delay)


def make_client(config: Config) -> TVClient:
    if config.platform == "firetv":
        return FireTVClient(config.address, adb_path=config.adb_path)
    return RokuClient(config.address)
