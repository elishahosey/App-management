from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def parse_clock(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid time {value!r}; use 24-hour HH:MM") from exc


@dataclass(frozen=True)
class Rule:
    name: str
    app_ids: frozenset[str]
    app_names: frozenset[str]
    days: frozenset[int]
    start: time
    end: time
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "Rule":
        day_values = data.get("days", list(DAY_NAMES))
        try:
            days = frozenset(DAY_NAMES.index(str(day).lower()[:3]) for day in day_values)
        except ValueError as exc:
            raise ValueError(f"Invalid day in rule {data.get('name', '<unnamed>')!r}") from exc
        apps = data.get("apps", [])
        app_ids = frozenset(str(app["id"]) for app in apps if app.get("id") is not None)
        app_names = frozenset(
            str(app["name"]).casefold() for app in apps if app.get("name")
        )
        if not app_ids and not app_names:
            raise ValueError(f"Rule {data.get('name', '<unnamed>')!r} has no apps")
        return cls(
            name=str(data.get("name", "unnamed rule")),
            app_ids=app_ids,
            app_names=app_names,
            days=days,
            start=parse_clock(str(data["start"])),
            end=parse_clock(str(data["end"])),
            enabled=bool(data.get("enabled", True)),
        )

    def active_at(self, moment: datetime) -> bool:
        if not self.enabled:
            return False
        current = moment.timetz().replace(tzinfo=None)
        weekday = moment.weekday()
        if self.start == self.end:
            return weekday in self.days
        if self.start < self.end:
            return weekday in self.days and self.start <= current < self.end
        if current >= self.start:
            return weekday in self.days
        previous_day = (moment - timedelta(days=1)).weekday()
        return previous_day in self.days and current < self.end

    def blocks(self, app_id: str, app_name: str, moment: datetime) -> bool:
        return self.active_at(moment) and (
            app_id in self.app_ids or app_name.casefold() in self.app_names
        )


def timezone_from_name(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            f"Unknown timezone {name!r}. On Windows, install the 'tzdata' package "
            "or use a timezone available on this computer."
        ) from exc

