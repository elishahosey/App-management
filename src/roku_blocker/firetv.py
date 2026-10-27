from __future__ import annotations

import re
import shutil
import subprocess

from .client import TVError
from .models import AppInfo


class FireTVClient:
    """Control Fire TV / Android TV devices through the official ADB tool."""

    def __init__(self, address: str, adb_path: str = "adb", timeout: float = 8.0):
        self.address = address if ":" in address else f"{address}:5555"
        self.adb_path = adb_path
        self.timeout = timeout
        if not shutil.which(adb_path):
            raise TVError(
                f"ADB executable {adb_path!r} was not found. Install Android SDK "
                "Platform-Tools and add adb to PATH, or set 'adb_path' in config."
            )

    def _run(self, *arguments: str, connect: bool = True) -> str:
        if connect:
            self._connect()
        command = [self.adb_path, "-s", self.address, *arguments]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise TVError(f"ADB command failed: {exc}") from exc
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()
            raise TVError(f"ADB command failed ({result.returncode}): {detail}")
        return result.stdout

    def _connect(self) -> None:
        try:
            result = subprocess.run(
                [self.adb_path, "connect", self.address],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise TVError(f"Could not connect to Fire TV: {exc}") from exc
        output = f"{result.stdout}\n{result.stderr}".casefold()
        if result.returncode or any(
            word in output for word in ("unable", "failed", "refused", "offline")
        ):
            raise TVError(
                f"Could not connect to Fire TV at {self.address}: "
                f"{(result.stderr or result.stdout).strip()}"
            )

    def apps(self) -> list[AppInfo]:
        output = self._run("shell", "pm", "list", "packages")
        packages = sorted(
            line.removeprefix("package:").strip()
            for line in output.splitlines()
            if line.startswith("package:")
        )
        return [AppInfo(package, package, "package") for package in packages]

    def active_app(self) -> AppInfo:
        outputs = [self._run("shell", "dumpsys", "activity", "activities")]
        patterns = (
            r"mResumedActivity:.*?\s([\w.]+)/",
            r"topResumedActivity=.*?\s([\w.]+)/",
            r"mFocusedApp=.*?\s([\w.]+)/",
            r"mCurrentFocus=.*?\s([\w.]+)/",
        )
        for output in outputs:
            for pattern in patterns:
                match = re.search(pattern, output)
                if match:
                    package = match.group(1)
                    return AppInfo(package, package, "package")
        outputs.append(self._run("shell", "dumpsys", "window", "windows"))
        for pattern in patterns:
            match = re.search(pattern, outputs[-1])
            if match:
                package = match.group(1)
                return AppInfo(package, package, "package")
        raise TVError("ADB connected, but the foreground Fire TV app could not be read")

    def go_home(self) -> None:
        self._run("shell", "input", "keyevent", "KEYCODE_HOME")

    def power_off(self) -> None:
        self._run("shell", "input", "keyevent", "KEYCODE_SLEEP")
