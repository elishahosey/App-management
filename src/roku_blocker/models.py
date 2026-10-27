from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppInfo:
    app_id: str
    name: str
    app_type: str = ""


# Backwards-compatible name for code written against version 0.1.
RokuApp = AppInfo


@dataclass(frozen=True)
class Device:
    location: str
    usn: str = ""
    server: str = ""

    @property
    def base_url(self) -> str:
        return self.location.rstrip("/")
