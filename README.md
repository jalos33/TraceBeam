# TraceBeam

A cross-platform (Windows / macOS / Linux) continuous LAN monitoring
dashboard — ping latency, packet loss, jitter, MOS, and per-hop route stats
(like `mtr`), graphed live. Same continuous-monitoring dashboard as the
WiPie project's LAN Monitor tab, rebuilt as a standalone desktop app with
only open-source dependencies.

Runs as a local web server (FastAPI) that opens your default browser — no
Electron, no bundled browser runtime, nothing proprietary.

---

## Quick Start

Two things matter before you start:

1. **Where to get it** — download a prebuilt executable (no Python needed),
   or run from source.
2. **Ping vs. hop stats** — basic latency/loss monitoring works immediately
   with no special permissions. The per-hop route view (the `mtr`-style
   feature) needs elevated privileges on every OS — that's not a bug, see
   [why below](#permissions).

### 1. Download

Go to the repo's **[Releases page](../../releases/latest)** and download the
zip for your OS (`TraceBeam-windows.zip`, `TraceBeam-macos.zip`, or
`TraceBeam-linux.zip`). No GitHub login required. Each zip unpacks to one
file: `TraceBeam` (`TraceBeam.exe` on Windows) — unzip steps are in
[Install & run](#2-install--run--step-by-step-per-os) below.

(Every push to `main` also builds and uploads per-commit artifacts under the
**[Actions tab](../../actions)**, if you want an unreleased dev build — those
do require being logged into GitHub and expire after 90 days.)

### 2. Install & run — step by step per OS

Each OS below has two paths: **normal** (ping/loss monitoring only, no
special permissions) and **elevated** (adds the `mtr`-style hop stats). Start
with normal — you can always quit and relaunch elevated later; nothing needs
reinstalling.

<details open>
<summary><strong>Windows</strong></summary>

**Normal (unprivileged):**

1. Unzip `TraceBeam-windows.zip` (right-click → **Extract All**). You'll get
   `TraceBeam.exe`.
2. Double-click `TraceBeam.exe`.
3. Windows SmartScreen will likely show *"Windows protected your PC"* since
   the executable isn't code-signed — click **More info** → **Run anyway**.
   This appears once per downloaded copy.
4. A console window opens (leave it running) and your browser opens
   automatically to the dashboard. If the browser doesn't open, go to
   `http://127.0.0.1:8742` yourself.
5. To stop TraceBeam, close the console window (or `Ctrl+C` inside it).

**Elevated (adds hop stats):**

1. Close any running normal instance first (see step 5 above — two instances
   can't share the same port).
2. Right-click `TraceBeam.exe` → **Run as administrator** → confirm the UAC
   prompt.
3. Same SmartScreen click-through as above the first time.

</details>

<details open>
<summary><strong>macOS</strong></summary>

**Normal (unprivileged):**

1. Unzip `TraceBeam-macos.zip` (double-click it in Finder, or
   `unzip TraceBeam-macos.zip` in Terminal). You'll get one file: `TraceBeam`.
2. Open Terminal and `cd` to wherever you unzipped it, e.g.:
   ```bash
   cd ~/Downloads
   ```
3. Make it executable (one-time):
   ```bash
   chmod +x TraceBeam
   ```
4. Run it:
   ```bash
   ./TraceBeam
   ```
5. Gatekeeper will likely block it the first time since it isn't signed by
   an Apple developer ID: *"TraceBeam cannot be opened because Apple cannot
   check it for malicious software."* Clear it once with either:
   ```bash
   xattr -d com.apple.quarantine ./TraceBeam
   ```
   ...or in Finder: right-click (Control-click) `TraceBeam` → **Open** →
   confirm **Open** in the dialog. Then re-run step 4.
6. Your browser opens automatically to the dashboard. If not, go to
   `http://127.0.0.1:8742` yourself.
7. To stop TraceBeam, go back to the Terminal window and press `Ctrl+C`.

**Elevated (adds hop stats):**

1. Stop any running normal instance first (`Ctrl+C` in its Terminal window —
   two instances can't share the same port).
2. From the same folder:
   ```bash
   sudo ./TraceBeam
   ```
3. Enter your macOS account password when prompted.

</details>

<details open>
<summary><strong>Linux</strong></summary>

**Normal (unprivileged):**

1. Unzip it:
   ```bash
   unzip TraceBeam-linux.zip
   ```
2. Make it executable (one-time):
   ```bash
   chmod +x TraceBeam
   ```
3. Run it:
   ```bash
   ./TraceBeam
   ```
4. Your browser opens automatically to the dashboard. If not, go to
   `http://127.0.0.1:8742` yourself.
5. To stop TraceBeam, go back to the terminal and press `Ctrl+C`.

**Elevated (adds hop stats) — two options:**

- **Recommended, no `sudo` needed for day-to-day use** — grant the binary
  just the one raw-socket capability, once:
  ```bash
  sudo setcap cap_net_raw+ep ./TraceBeam
  ```
  From then on, run it normally (`./TraceBeam`, no `sudo`) and hop stats
  just work.
- **Quick/one-off:**
  ```bash
  sudo ./TraceBeam
  ```

Either way, stop any running normal instance first (two instances can't
share the same port).

</details>

### 3. It's running

A browser tab opens automatically at `http://127.0.0.1:8742` with three
seeded targets (`8.8.8.8`, `1.1.1.1`, `google.com`) already collecting data.
Add your own target (router IP, a server you care about, etc.) from the
toolbar at the top. The header shows a live roll-up (e.g. "4 targets · 3
ok · 1 down") of everything you're watching.

Each row has three actions: **⏸ pause** (stop sampling without losing
history — the row dims and shows a "paused" tag), **✎ rename**, and **✕
remove** (deletes the target and its history).

Click any target row to open its detail view — latency timeline chart plus
the **Route / Hops** table, with a **⬇ CSV** button to download that
window's data. If the hop table says *"Hop data needs elevated
privileges"*, that's expected on a normal (non-admin) launch — see the
**Elevated** steps for your OS in [Install & run](#2-install--run--step-by-step-per-os)
above to enable it.

---

## Permissions — why elevation is needed at all

TraceBeam sends ICMP via raw sockets (through `icmplib`, pure Python — no
shelling out to `ping`/`mtr`, which behave inconsistently across OSes). Raw
sockets are privileged on most systems, but **how much** privilege you need
depends on the feature:

- **Ping monitoring** (the main "All Targets" latency/loss view) runs
  **unprivileged** on macOS and most Linux setups — no admin, no sudo. This
  is the common case; the Quick Start commands above already cover it.
- **Per-hop route stats** (the "Route / Hops" detail view) always need a raw
  socket on every OS, because setting the TTL per-probe requires one. There
  is no unprivileged fallback for this — it's inherent to how traceroute
  works, the same reason the system `mtr`/`traceroute` binaries need
  root/setuid too.

**Prefer least privilege — don't reach for root/admin unless you actually
want hop stats.** On Linux specifically, `setcap` (see the Linux **Elevated**
steps above) is better than `sudo` long-term: it grants the binary just the
one raw-socket capability and otherwise runs as your normal user, so it
can't leave root-owned files behind.

> **Why avoid running the whole app as root/sudo where you can:** it makes
> the database and data directory root-owned, which can make a later
> non-root run fail to open its own files (see
> [Troubleshooting](#troubleshooting) if that happens).

---

## FAQ

**Do I need Python installed to run the downloaded executable?** No. The
Releases zips are self-contained (PyInstaller-built) — no Python, no `pip
install`, nothing else to set up. Python is only needed if you choose
[Running from source](#running-from-source).

**Is it safe to run this as admin/root?** The elevated launch only grants
raw-socket access for the hop-stats feature — TraceBeam makes no network
calls out, accepts no credentials, and shells out to nothing (see
[Security](#security)). That said, prefer the least-privilege option for
your OS (Linux `setcap`, in particular) over blanket `sudo`/Administrator
when you can — see [Permissions](#permissions--why-elevation-is-needed-at-all).

**Why does my OS say this is from an "unidentified developer" / block it
with SmartScreen?** The executables aren't code-signed (that requires a paid
Apple Developer ID or Windows code-signing certificate). This is a
distribution-trust warning, not a vulnerability report — see
[Security](#security) for why, and the per-OS steps in
[Install & run](#2-install--run--step-by-step-per-os) for how to get past it.

**Does TraceBeam send my data anywhere / phone home?** No. It binds to
`127.0.0.1` by default, makes no outbound calls, and the only thing it does
over the network is ping/traceroute the targets you configure. Everything it
collects stays in a local SQLite file — see [Security](#security).

**Can other devices on my LAN open the dashboard?** Not by default — it
binds to `127.0.0.1` (localhost only). You'd have to deliberately set
`server.host: 0.0.0.0` in `config.yaml` (see [Configuration](#configuration)),
and doing so exposes the dashboard to your whole network with no
authentication, so only do it if you understand that tradeoff.

**Does closing the browser tab stop monitoring?** No. Sampling runs in the
TraceBeam server process itself (a background scheduler), independent of any
open browser tab — closing or reopening the tab just reconnects to data
that kept collecting. To actually stop monitoring, stop the process itself
(`Ctrl+C` in its terminal/console window, or close the window on Windows).

**How is this different from just running `ping`/`mtr` myself?** TraceBeam
continuously samples multiple targets in the background, stores history
(latency, loss, jitter, MOS, hop data) in a local database, and graphs it
live in a browser dashboard — rather than a one-off terminal snapshot. It
also doesn't shell out to the OS `ping`/`mtr`/`traceroute` binaries at all;
it speaks ICMP directly via `icmplib` for consistent behavior across OSes.

**Can I change the seeded ping targets, sample interval, or port?** Yes —
see [Configuration](#configuration). You can also add/rename/pause/remove
targets live from the dashboard toolbar without touching config files.

**How do I reset all history / start fresh?** Stop TraceBeam, then delete
the SQLite DB file (see [Configuration](#configuration) for its per-OS
path). It's recreated empty on next launch.

---

## Troubleshooting

**"Address already in use" / server won't start.** Another TraceBeam instance
(privileged or not) is already bound to port 8742. Find and stop it:

```bash
# macOS / Linux
lsof -i :8742          # note the PID
kill <PID>

# Windows (PowerShell)
Get-Process -Id (Get-NetTCPConnection -LocalPort 8742).OwningProcess
Stop-Process -Id <PID>
```

**Hop table still says "needs elevated privileges" even after using
`sudo`/admin.** Make sure you're running the *same* executable you expect,
and that nothing cached an older unprivileged instance on the same port (see
above — stop it first, then relaunch elevated).

**Ran once with `sudo`, now a normal (non-sudo) launch fails to read/write
its database.** The DB became root-owned from the earlier `sudo` run. Either
keep launching with `sudo` going forward, switch to the Linux `setcap`
approach (no root needed at all), or reset by removing the data directory
(you'll lose history): see [Configuration](#configuration) below for its
exact path per OS.

**Downloaded on macOS/Windows and it won't launch at all ("unidentified
developer" / SmartScreen block with no way through).** See the Gatekeeper /
SmartScreen steps in [Install & run](#2-install--run--step-by-step-per-os) —
both are one-time first-run approvals for unsigned executables, not an error
in the app.

**Launched it and the browser tab is blank / "can't connect" for several
seconds.** Normal on first launch of any given build — macOS/Windows
security scanning an unsigned executable it hasn't seen before can add a
several-second delay before the server actually starts responding.
Subsequent launches of the same executable are fast. Give it ~10 seconds
before assuming something's wrong.

**macOS/Linux: `zsh: permission denied: ./TraceBeam` (or `bash:` /
`Permission denied`).** You skipped (or it didn't take) the one-time
`chmod +x TraceBeam` step — run it, then try `./TraceBeam` again.

**Ping/loss monitoring works but hop stats never populate, even without any
error shown.** Confirm you actually launched the elevated variant for your
OS — a normal launch silently shows empty hop data by design (see
[Permissions](#permissions--why-elevation-is-needed-at-all)), it doesn't
error out. Re-launch using the **Elevated** steps for your OS in
[Install & run](#2-install--run--step-by-step-per-os).

**Linux `setcap` step fails with "command not found."** Install
`libcap2-bin` first: `sudo apt install libcap2-bin` (Debian/Ubuntu) — most
other distros ship it preinstalled. See
[Running from source](#running-from-source) for the equivalent note.

---

## Running from source

Prefer this if you want to modify the code, or your OS/architecture doesn't
have a prebuilt artifact. Requires **Python 3.10+** (developed and packaged
on 3.12 — if `python3 --version` shows something older, install a newer
Python first).

```bash
# 1. Get a virtual environment
python3 -m venv .venv

# 2. Activate it
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows (PowerShell / cmd)

# 3. Install the Python dependencies
pip install -r requirements.txt

# 4. Run (ping-only, unprivileged)
python -m tracebeam.main

# ...or for hop stats too:
sudo .venv/bin/python -m tracebeam.main   # macOS/Linux
```

### Python dependencies (all open source, installed by step 3)

| Package | License | Purpose |
|---------|---------|---------|
| `fastapi` | MIT | Web framework / API |
| `starlette` | BSD | ASGI toolkit (FastAPI core) |
| `uvicorn[standard]` | BSD | ASGI server |
| `sqlalchemy` | MIT | SQLite ORM |
| `apscheduler` | MIT | Background sampling scheduler |
| `pyyaml` | MIT | Config file parsing |
| `icmplib` | LGPL-3.0 | Pure-Python ICMP ping / traceroute |
| `platformdirs` | MIT | Per-OS config & data directories |

No system libraries or external binaries are required on any OS — TraceBeam
does **not** depend on the OS `ping`, `mtr`, or `traceroute` binaries. On
Linux, if you want `setcap` (see Permissions above), it ships in
`libcap2-bin` (`sudo apt install libcap2-bin` on Debian/Ubuntu — preinstalled
on most distros).

---

## Configuration

TraceBeam reads `config.yaml` from, in order:

1. Your OS config directory (`platformdirs`):
   - Windows: `%APPDATA%\TraceBeam\TraceBeam\config.yaml`
   - macOS: `~/Library/Application Support/TraceBeam/config.yaml`
   - Linux: `~/.config/TraceBeam/config.yaml`
2. `config.yaml` in the current working directory
3. The bundled default

Copy the repo's `config.yaml` to location (1) to customize. Options:

```yaml
server:
  host: 127.0.0.1        # local-only. Change to 0.0.0.0 only if you understand
  port: 8742             # the LAN-exposure tradeoff (see Security)
lan:
  ping_targets: [8.8.8.8, 1.1.1.1, google.com]
  sample_interval_seconds: 2
  mtr_interval_seconds: 45
  mtr_cycles: 5
  raw_retention_hours: 48   # raw per-probe samples
  retention_days: 30        # per-minute rollups
```

Data (the SQLite DB) is stored in the same OS-specific directory as the
config, e.g. `~/Library/Application Support/TraceBeam/tracebeam.db` on macOS.

---

## Building a standalone executable

Must be built natively on each target OS — PyInstaller does not
cross-compile. `.github/workflows/build.yml` runs a matrix build (Windows /
macOS / Linux) on every push and uploads all three artifacts; that's the
easiest way to get all three without owning all three machines.

To build locally for the current OS:

```bash
pip install pyinstaller
pyinstaller packaging/tracebeam.spec --distpath dist --workpath build
```

Produces a single-file executable at `dist/TraceBeam` (`dist/TraceBeam.exe` on
Windows). Note this local build is unsigned too, same as the CI artifacts —
the Gatekeeper/SmartScreen steps above still apply.

Run it the same way as a downloaded build (see
[Quick Start](#quick-start)), just from `dist/` instead of wherever you
unzipped a download:

```bash
./dist/TraceBeam              # ping/loss monitoring only

sudo ./dist/TraceBeam         # + hop stats (macOS/Linux; see Permissions)
```

---

## License

MIT — see [`LICENSE`](LICENSE). Third-party dependency licenses (including
an explicit note on `icmplib`'s LGPL-3.0 terms as bundled into the prebuilt
executables) are in [`NOTICE.md`](NOTICE.md).

## Security

- **Every dependency is open source** (MIT / BSD / LGPL). Additions
  are vetted for license and known CVEs before inclusion — see
  `.claude/skills/dependency-security-audit/`. CI runs `pip-audit` against
  `requirements.txt` on every build.
- **No credential handling.** TraceBeam never prompts for, receives, or stores
  a password. Privilege elevation (`setcap` / `sudo` / Administrator) is
  performed by the OS *before* the process starts; the app just inherits the
  raised privilege. It makes no `subprocess`/shell calls and reads no
  environment variables, so there is no path for a secret to be captured.
- **Only disk artifact is the local SQLite DB**, which holds ping-target
  names, RTT numbers, timestamps, and network-hop IPs/hostnames — never
  credentials.
- **Binds to `127.0.0.1` by default**, not `0.0.0.0`. It's a single-user
  local app, so there's no network-facing auth to misconfigure. Only set
  `server.host: 0.0.0.0` if you deliberately want LAN access, and understand
  that exposes the dashboard to your whole network with no authentication.
- **Chart.js is vendored locally** (`tracebeam/static/js/vendor/`) rather than
  loaded from a CDN, so there's no live third-party script dependency and the
  app works fully offline.
- **Unsigned executables**: CI-built artifacts aren't code-signed (that
  requires a paid Apple Developer ID / Windows code-signing certificate),
  which is why Gatekeeper/SmartScreen flag them on first run. This is a
  distribution-trust warning, not a vulnerability — the build is reproducible
  from this source via the same `pip-audit`-gated CI workflow anyone can
  read.
