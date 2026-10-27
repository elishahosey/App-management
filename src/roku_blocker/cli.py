from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from .blocker import AppBlocker
from .config import Config
from .client import TVError
from .firetv import FireTVClient
from .roku import RokuClient, RokuError, discover
from .schedule import timezone_from_name


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        prog="tv-blocker",
        description="Block selected smart TV apps on a schedule.",
    )
    command.add_argument("--verbose", action="store_true", help="enable debug logging")
    subcommands = command.add_subparsers(dest="command", required=True)

    find = subcommands.add_parser("discover", help="find Roku devices on this network")
    find.add_argument("--timeout", type=float, default=3.0)

    apps = subcommands.add_parser("apps", help="list apps installed on a TV")
    apps.add_argument("address", help="TV URL or IP address")
    apps.add_argument("--platform", choices=("firetv", "roku"), default="firetv")
    apps.add_argument("--adb-path", default="adb")

    validate = subcommands.add_parser("validate", help="validate a configuration file")
    validate.add_argument("-c", "--config", default="config.json")

    check = subcommands.add_parser("check", help="perform one check")
    check.add_argument("-c", "--config", default="config.json")
    check.add_argument("--dry-run", action="store_true", help="report without enforcing")

    run = subcommands.add_parser("run", help="monitor continuously")
    run.add_argument("-c", "--config", default="config.json")

    sample = subcommands.add_parser("write-sample", help="write a sample config file")
    sample.add_argument("path", nargs="?", default="config.json")
    return command


def normalize_roku_url(value: str) -> str:
    value = value.rstrip("/")
    return value if "://" in value else f"http://{value}:8060"


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    configure_logging(args.verbose)
    try:
        if args.command == "discover":
            devices = discover(args.timeout)
            if not devices:
                print("No Roku devices found. Check the troubleshooting guide in README.md.")
                return 1
            for device in devices:
                client = RokuClient(device.base_url)
                try:
                    name = client.device_name()
                except RokuError:
                    name = "Unknown Roku"
                print(f"{name}\t{device.base_url}\t{device.usn}")
            return 0

        if args.command == "apps":
            client = (
                FireTVClient(args.address, args.adb_path)
                if args.platform == "firetv"
                else RokuClient(normalize_roku_url(args.address))
            )
            print("APP ID\tTYPE\tNAME")
            for app in client.apps():
                print(f"{app.app_id}\t{app.app_type}\t{app.name}")
            return 0

        if args.command == "write-sample":
            destination = Path(args.path)
            if destination.exists():
                print(f"Refusing to overwrite existing file: {destination}", file=sys.stderr)
                return 2
            source = Path(__file__).parents[2] / "config.example.json"
            destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Wrote {destination}")
            return 0

        config = Config.load(args.config)
        if args.command == "validate":
            print(
                f"Valid: {len(config.rules)} rule(s), timezone {config.timezone}, "
                f"{config.platform} device {config.address}"
            )
            return 0

        blocker = AppBlocker(config)
        if args.command == "check":
            app = blocker.client.active_app()
            moment = datetime.now(timezone_from_name(config.timezone))
            matches = blocker.matching_rules(app, moment)
            print(
                json.dumps(
                    {
                        "time": moment.isoformat(),
                        "app": {"id": app.app_id, "name": app.name},
                        "blocked": bool(matches),
                        "matching_rules": matches,
                        "enforced": bool(matches) and not args.dry_run,
                    },
                    indent=2,
                )
            )
            if matches and not args.dry_run:
                blocker.check_once(moment)
            return 3 if matches else 0

        blocker.run_forever()
        return 0
    except (ValueError, TVError, RokuError, OSError) as exc:
        logging.getLogger("roku_blocker").error("%s", exc)
        return 2
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
