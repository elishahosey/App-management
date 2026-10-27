# TV App Blocker

A small Python service that watches the active app on a supported smart TV and
sends the TV back to its Home screen when that app is blocked by the current schedule.
It runs entirely on your home network and does not need a cloud account.

## Compatibility and network scope

This version targets **Amazon/Insignia Fire TV editions** and **Roku**. The same
Python service works on ordinary apartment Wi-Fi, a personal router, or
Ethernet; the router brand and internet provider do not matter. What matters is
that the always-on computer can reach the TV on the local network.

It will not work through a guest network that isolates wireless clients or
across the public internet. Google TV/Android TV can use a future ADB adapter
variant, while Apple TV, Samsung Tizen, and LG webOS need their own adapters.
Those platforms expose different control APIs.

If you later need remote control from outside the apartment, use a private VPN
into the home network (for example, WireGuard or Tailscale) and add
authentication before exposing any dashboard. Do not port-forward Roku's ECP
port or a future management page directly to the internet.

## Identify your Insignia platform

On the TV, open Settings. If you see **My Fire TV** or **Device & Software**,
use `"platform": "firetv"`. If the home screen says Roku, use `"platform":
"roku"`. If neither is present, find the model number under Settings > Device
Information or on the rear label; this build may need another adapter.

## Important limitations

This is practical household automation, not an unbypassable parental-control
system. Someone with access to developer settings, the host computer, or the
network can disable it. A blocked app may be visible briefly between polls.

Roku's External Control Protocol (ECP) does **not** expose a parental-control
API that prevents an app from opening. This project enforces a rule by polling
the active app (every two seconds by default) and issuing a `Home` keypress.
Someone can therefore see a blocked app briefly, and a determined person with
network or computer access can bypass this. Treat it as a practical household
automation, not a security boundary.

For Fire TV, the service uses ADB debugging. ADB grants powerful local control,
so approve only your own old computer and never expose port 5555 to the public
internet.

## Fire TV setup (Insignia)

1. Install Google's Android SDK Platform-Tools so the `adb` command is on PATH.
2. On Fire TV, open Settings > My Fire TV (or Device & Software) > Developer
   Options and enable **ADB Debugging**. If Developer Options is hidden, select
   About and press the center button on the TV name seven times.
3. Find the TV IP under Settings > My Fire TV > About > Network.
4. From the old computer, run `adb connect TV_IP:5555`.
5. Accept the authorization prompt on the TV and choose **Always allow from
   this computer**.
6. Run `tv-blocker apps TV_IP --platform firetv`. Fire TV app identifiers are
   Android package names such as `com.netflix.ninja`.

For Roku, the computer and Roku must be on the same local network. Turn on:

`Settings > System > Advanced system settings > Control by mobile apps > Enabled`

Menu wording may vary by model. Restricting network access for mobile apps will
stop the blocker from sending `Home`.

## Quick start

You need Python 3.10 or newer.

### Windows

Open PowerShell in this project folder:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
$tvAddress = Read-Host "TV IP address"
tv-blocker apps $tvAddress --platform firetv
tv-blocker write-sample config.json
Copy-Item .env.example .env
```

Edit `.env` with the TV address, timezone, and app details you want to use.

### Linux / Raspberry Pi

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
read -r -p "TV IP address: " tv_address
tv-blocker apps "$tv_address" --platform firetv
tv-blocker write-sample config.json
cp .env.example .env
```

Edit `.env` with your TV address, timezone, and app details. Use the URL printed
by `discover` and the IDs printed by `apps`. App IDs are more reliable than
names, so keep the ID; the name is also useful as a readable fallback.

Then validate and try one safe check:

```bash
tv-blocker validate --config config.json
tv-blocker check --config config.json --dry-run
tv-blocker run --config config.json
```

Stop the foreground service with Ctrl+C. Remove `--dry-run` from `check` to
enforce a single check. A blocked result deliberately exits with code `3`;
configuration or connection errors exit with code `2`.

## Configuration

The sample config reads device and rule-specific strings from environment
variables. Copy `.env.example` to `.env` and edit the values:

```dotenv
TV_PLATFORM=firetv
TV_ADDRESS=192.0.2.10:5555
TIMEZONE=Etc/UTC
BLOCKED_APP_ID=com.example.app
BLOCKED_APP_NAME=Example app
```

`config.json` is based on [config.example.json](config.example.json) and uses
`${VARIABLE}` references. The app loads `.env` from the same directory as the
config file. Variables already set in the process environment take precedence;
an unset referenced variable causes a validation error. Keep your real `.env`
and `config.json` local; both are ignored by Git.

- Times use local 24-hour `HH:MM` notation.
- The start is included; the end is excluded.
- An overnight window belongs to the day it starts.
- Equal start and end times mean all day on each selected day.
- `action` can be `home`, or `poweroff` for a Roku TV that supports the
  `PowerOff` ECP key. Start with `home`.
- A shorter poll interval reacts faster but makes more network requests. Two
  seconds is a reasonable start.
- `cooldown_seconds` prevents repeated remote presses while the screen changes.
- `.env` and `config.json` are ignored by Git so device details and personal
  schedules are not accidentally committed.

To block another app or time period, add another object to `rules`. To share one
schedule between apps, add more objects to that rule's `apps` array.

## Running all day on an old computer

The best host is a machine that:

- can stay powered on and connected to the same router as the Roku;
- does not sleep or hibernate;
- has a reserved/static DHCP address for the Roku (configured in your router);
- automatically starts the blocker after a reboot.

An old laptop works well. Disable sleep while plugged in, but allow the display
to turn off. Ethernet is preferable when convenient. This process is tiny:
it sleeps between short local HTTP requests and needs no monitor once set up.

### Windows automatic startup

1. Complete the Windows quick start above and verify `tv-blocker run`.
2. Open **Task Scheduler**, choose **Create Task**, and use:
   - Trigger: **At startup**
   - Action: **Start a program**
   - Program: the full path to
     `deployment\start-tv-blocker.cmd`
   - Select **Run whether user is logged on or not**
   - Select **Restart the task if it fails**
3. In the Conditions tab, clear “Start the task only if the computer is on AC
   power” if appropriate for your machine.
4. Reboot and inspect `tv-blocker.log` in the project folder.

The included command file resolves the project directory relative to itself, so
the project and `.venv` can live anywhere. If OneDrive file availability is a
concern, mark the whole folder “Always keep on this device,” or copy it to a
plain local folder such as `C:\tv-app-blocker`.

### Linux automatic startup with systemd

For a dedicated Linux box or Raspberry Pi, copy the project to
`/opt/tv-app-blocker`, create its virtual environment, and test it. Then:

```bash
sudo cp deployment/tv-blocker.service /etc/systemd/system/
sudoedit /etc/systemd/system/tv-blocker.service
sudo systemctl daemon-reload
sudo systemctl enable --now tv-blocker
systemctl status tv-blocker
journalctl -u tv-blocker -f
```

Replace `YOUR_USER` and paths in the service template first. `systemd` starts it
at boot, restarts it after a failure, and stores logs in the journal.

## Troubleshooting

**Discovery finds nothing**

- Confirm both devices are on the same non-guest network. Guest Wi-Fi and
  “client/AP isolation” often block device-to-device traffic.
- Enable “Control by mobile apps” on the Roku.
- Allow Python through the host firewall on private networks. Discovery uses
  SSDP multicast UDP port 1900.
- Discovery is optional: find the Roku IP under
  `Settings > Network > About`, then run
  `tv-blocker apps <IP> --platform roku`.

**The Roku appears offline later**

Reserve its IP address in the router, then keep that address in `config.json`.
The monitor uses exponential retry delays up to 60 seconds during outages.

**It detects an app but cannot close it**

The app queries can work even when keypress control is disabled. Re-check the
Roku “Control by mobile apps” setting. Also confirm that `action` is `home`.

**Time rules are wrong**

Run `tv-blocker check --dry-run` and inspect its ISO timestamp. Set
`timezone` to an IANA name such as `America/Chicago`, not `CST`. Windows
installs the small `tzdata` package automatically with this project.

## How it works

The design separates four concerns:

1. `roku.py` speaks Roku ECP: SSDP discovers the TV; HTTP endpoints list and
   inspect apps; an HTTP POST simulates a remote key.
2. `schedule.py` turns configuration into rules and handles normal,
   overnight, and all-day intervals using timezone-aware datetimes.
3. `blocker.py` is the policy loop. It checks the active app, asks each active
   rule whether it matches, enforces the action, and backs off on network errors.
4. `firetv.py` invokes ADB as a subprocess, reads the current Android package,
   and sends the Android Home key.
5. `cli.py` provides commands for setup, validation, one-shot diagnosis, and
   continuous operation.

The client uses Python's standard `urllib`, `socket`, and XML parser directly.
This avoids depending on a Roku wrapper and makes the protocol visible for
learning. If you later adopt the asynchronous `rokuecp` library, only the client
boundary should need to change.

### Why app IDs and names?

Roku returns both. IDs avoid capitalization and localization problems; names
make the configuration readable and provide a fallback. A rule matches either.

### Why polling?

ECP provides a query for the active app, but not a subscription that pushes
every app change to this program. Polling is the simplest reliable mechanism.
The cooldown avoids sending several Home presses during the reaction window.

### Why a service instead of a daily scheduler?

A daily job can start or stop something at fixed times, but multiple schedules,
overnight ranges, weekday rules, and future features quickly become awkward.
A lightweight long-running process keeps the policy in one testable place.

## Extending it

Natural next steps are:

- a local web interface for editing schedules;
- temporary “allow for 15 minutes” overrides;
- PIN-protected configuration;
- notifications and usage reports;
- multiple Roku devices;
- plug-in device adapters for other TV platforms;
- router/DNS-level blocking for stronger enforcement.

Keep new device-specific code behind a client interface like `RokuClient`, and
keep policy decisions in `AppBlocker`. That separation makes testing possible
without a physical television.

For another TV platform, first research whether it can report the foreground
app and accept a remote-control command on the LAN. Implement those two
operations behind a new client adapter, then reuse the schedule and policy
layers. A DNS-based fallback is more network-portable, but streaming apps use
changing sets of login, advertising, API, and video-delivery domains; blocking
them can be incomplete or can break unrelated services.

## Tests and development

```bash
python -m unittest discover -s tests -v
python -m roku_blocker --help
```

The tests cover schedule boundaries, overnight behavior, app matching, dry
runs, enforcement, and case-insensitive SSDP headers.

## Learning resources

- [Roku External Control Protocol documentation](https://developer.roku.com/dev/docs/external-control-api):
  the authoritative reference for SSDP discovery, `/query/apps`,
  `/query/active-app`, and `/keypress/Home`.
- [Python `urllib.request`](https://docs.python.org/3/library/urllib.request.html):
  the HTTP client used for ECP requests.
- [Python `socket`](https://docs.python.org/3/library/socket.html):
  the UDP networking layer used for SSDP discovery.
- [Python `xml.etree.ElementTree`](https://docs.python.org/3/library/xml.etree.elementtree.html):
  parsing Roku's XML responses.
- [Python `datetime` and `zoneinfo`](https://docs.python.org/3/library/zoneinfo.html):
  timezone-aware schedule evaluation.
- [Python virtual environments](https://docs.python.org/3/tutorial/venv.html):
  isolating the install on the always-on computer.
- [Microsoft Task Scheduler fundamentals](https://learn.microsoft.com/windows/win32/taskschd/task-scheduler-start-page):
  starting and supervising the tool on Windows.
- [`systemd` service documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html):
  running the tool at boot on Linux.
- [Amazon: connect to Fire TV through ADB](https://developer.amazon.com/docs/fire-tv/connecting-adb-to-device.html):
  enabling debugging, authorizing the computer, and connecting on the LAN.
- [Android Debug Bridge documentation](https://developer.android.com/tools/adb):
  how ADB clients, servers, devices, shell commands, and authorization work.
- [`rokuecp` on PyPI](https://pypi.org/project/rokuecp/):
  a maintained asynchronous Roku Python client to study if the project grows.

## Privacy and security

No telemetry or cloud calls are implemented. Traffic remains on your LAN.
Anyone who can edit `config.json`, stop the service, change the Roku setting, or
isolate the host from the network can bypass it. Use normal operating-system
accounts and file permissions if the schedule needs protection.
