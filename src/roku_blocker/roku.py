from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from .client import TVError
from .models import AppInfo, Device


class RokuError(TVError):
    pass


class RokuClient:
    def __init__(self, base_url: str, timeout: float = 4.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, path: str, method: str = "GET") -> bytes:
        request = urllib.request.Request(
            f"{self.base_url}/{path.lstrip('/')}",
            method=method,
            data=b"" if method == "POST" else None,
            headers={"User-Agent": "roku-app-blocker/0.1"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RokuError(f"Roku request failed: {exc}") from exc

    def device_name(self) -> str:
        root = self._xml("query/device-info")
        return (
            root.findtext("user-device-name")
            or root.findtext("friendly-device-name")
            or root.findtext("model-name")
            or self.base_url
        )

    def apps(self) -> list[AppInfo]:
        root = self._xml("query/apps")
        return [
            AppInfo(
                app_id=element.attrib.get("id", ""),
                name=(element.text or "").strip(),
                app_type=element.attrib.get("type", ""),
            )
            for element in root.findall("app")
        ]

    def active_app(self) -> AppInfo:
        root = self._xml("query/active-app")
        element = root.find("app")
        if element is None:
            return AppInfo("", "")
        return AppInfo(
            app_id=element.attrib.get("id", ""),
            name=(element.text or "").strip(),
            app_type=element.attrib.get("type", ""),
        )

    def keypress(self, key: str) -> None:
        self._request(f"keypress/{key}", method="POST")

    def go_home(self) -> None:
        self.keypress("Home")

    def power_off(self) -> None:
        self.keypress("PowerOff")

    def _xml(self, path: str) -> ET.Element:
        try:
            return ET.fromstring(self._request(path))
        except ET.ParseError as exc:
            raise RokuError(f"Roku returned malformed XML for {path}: {exc}") from exc


def discover(timeout: float = 3.0) -> list[Device]:
    destination = ("239.255.255.250", 1900)
    message = (
        'M-SEARCH * HTTP/1.1\r\n'
        'HOST: 239.255.255.250:1900\r\n'
        'MAN: "ssdp:discover"\r\n'
        'MX: 2\r\n'
        'ST: roku:ecp\r\n\r\n'
    ).encode("ascii")
    devices: dict[str, Device] = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        sock.settimeout(0.25)
        sock.sendto(message, destination)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                payload, _ = sock.recvfrom(65535)
            except socket.timeout:
                continue
            headers = _parse_ssdp_headers(payload)
            location = headers.get("location", "")
            if location:
                devices[location] = Device(
                    location=location,
                    usn=headers.get("usn", ""),
                    server=headers.get("server", ""),
                )
    finally:
        sock.close()
    return sorted(devices.values(), key=lambda device: device.location)


def _parse_ssdp_headers(payload: bytes) -> dict[str, str]:
    lines = payload.decode("utf-8", errors="replace").splitlines()[1:]
    headers: dict[str, str] = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    return headers
