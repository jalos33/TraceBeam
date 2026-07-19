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

Go to the repo's **[Actions tab](../../actions)**, click the most recent
green **Build** run, scroll to **Artifacts**, and download the zip for your
OS (`TraceBeam-windows`, `TraceBeam-macos`, or `TraceBeam-linux`). You'll need
to be logged into GitHub with access to this repo — artifacts aren't public.
Unzip it; you'll have one file: `TraceBeam` (`TraceBeam.exe` on Windows).

### 2. First run — per OS

**macOS**

```bash
cd ~/Downloads          # or wherever you unzipped it
chmod +x TraceBeam
./TraceBeam
```

Gatekeeper will likely block it the first time since it isn't signed by an
Apple developer ID: *"TraceBeam cannot be opened because Apple cannot check
it for malicious software."* Fix it once with either:

```bash
xattr -d com.apple.quarantine ./TraceBeam
```

...or in Finder: right-click (Control-click) `TraceBeam` → **Open** →
confirm **Open** in the dialog. After that first approval it runs normally.

**Windows**

Double-click `TraceBeam.exe`. SmartScreen will likely show *"Windows
protected your PC"* since it's unsigned — click **More info** → **Run
anyway**. This appears once per download.

**Linux**

```bash
chmod +x TraceBeam
./TraceBeam
```

### 3. It's running

A browser tab opens automatically at `http://127.0.0.1:8742` with three
seeded targets (`8.8.8.8`, `1.1.1.1`, `google.com`) already collecting data.
Add your own target (router IP, a server you care about, etc.) from the
toolbar at the top.

Click any target row to open its detail view — latency timeline chart plus
the **Route / Hops** table. If that table says *"Hop data needs elevated
privileges"*, that's expected on a normal (non-admin) launch — see the next
section to enable it.

### 4. Want to see hop stats (the `mtr`-style view)?

Ping/loss monitoring already works with the command above. To also populate
the **Route / Hops** table, relaunch with elevated privileges:

| OS | Command |
|----|---------|
| **macOS** | `sudo ./TraceBeam` |
| **Linux (recommended, no root needed)** | `sudo setcap cap_net_raw+ep ./TraceBeam` once, then just `./TraceBeam` normally from then on |
| **Linux (quick/one-off)** | `sudo ./TraceBeam` |
| **Windows** | Right-click `TraceBeam.exe` → **Run as administrator** |

If something's already using the port (e.g. an earlier unprivileged run you
forgot to stop), stop that one first — see
[Troubleshooting](#troubleshooting).

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
want hop stats.** On Linux specifically, `setcap` (see table above) is
better than `sudo` long-term: it grants the binary just the one raw-socket
capability and otherwise runs as your normal user, so it can't leave
root-owned files behind.

> **Why avoid running the whole app as root/sudo where you can:** it makes
> the database and data directory root-owned, which can make a later
> non-root run fail to open its own files (see
> [Troubleshooting](#troubleshooting) if that happens).

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
SmartScreen steps in [Quick Start](#quick-start) — both are one-time
first-run approvals for unsigned executables, not an error in the app.

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
