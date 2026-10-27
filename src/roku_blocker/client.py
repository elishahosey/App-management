from __future__ import annotations

from typing import Protocol

from .models import AppInfo


class TVError(RuntimeError):
    pass


class TVClient(Protocol):
    def apps(self) -> list[AppInfo]: ...

    def active_app(self) -> AppInfo: ...

    def go_home(self) -> None: ...

    def power_off(self) -> None: ...
