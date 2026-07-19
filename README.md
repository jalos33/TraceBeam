# NetPulse

A cross-platform (Windows / macOS / Linux) continuous LAN monitoring
dashboard — ping latency, packet loss, jitter, MOS, and per-hop route stats,
graphed live. Same PingPlotter-style dashboard as the WiPie project's LAN
Monitor tab, rebuilt as a standalone desktop app with only open-source
dependencies.

Runs as a local web server (FastAPI) that opens your default browser — no
Electron, no bundled browser runtime, nothing proprietary.

---

## Install & run

There are two ways to run NetPulse. The prebuilt executable needs **nothing
installed**; running from source needs Python.

### Option A — Prebuilt executable (recommended, zero dependencies)

Download the executable for your OS from the
[Actions build artifacts](../../actions) (or a release), then:

| OS | File | Run it |
|----|------|--------|
| **Windows** | `NetPulse.exe` | Double-click it, or `NetPulse.exe` in a terminal |
| **macOS** | `NetPulse` | `./NetPulse` in Terminal (see [Permissions](#permissions) for hop stats) |
| **Linux** | `NetPulse` | `chmod +x NetPulse && ./NetPulse` |

It starts a local server and opens `http://127.0.0.1:8742` in your default
browser automatically. The executable is fully self-contained — Python and
all libraries are bundled inside it. There are **no system packages to
install**: NetPulse talks ICMP directly via raw sockets and does **not**
depend on the OS `ping`, `mtr`, or `traceroute` binaries.

### Option B — From source

Requires **Python 3.10 or newer** (developed and packaged on 3.12).

```bash
# 1. Get a virtual environment
python3 -m venv .venv

# 2. Activate it
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows (PowerShell / cmd)

# 3. Install the Python dependencies
pip install -r requirements.txt

# 4. Run
python -m netpulse.main
```

#### Python dependencies (all open source, installed by step 3)

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

No system libraries or external binaries are required on any OS. On Linux, if
you want to grant raw-socket capability without running as root (see below),
you need the `setcap` tool, which ships in `libcap2-bin`
(`sudo apt install libcap2-bin` on Debian/Ubuntu — preinstalled on most
distros).

---

## Permissions

NetPulse sends ICMP via raw sockets (through `icmplib`, pure Python — no
shelling out to `ping`/`mtr`, which behave inconsistently across OSes). Raw
sockets are privileged on most systems, but **how much** privilege you need
depends on which feature you use:

- **Ping monitoring** (the main "All Targets" latency/loss view) runs
  **unprivileged** on macOS and most Linux setups — no admin, no sudo. This
  is the common case; just run the app normally.
- **Per-hop route stats** (the "Route / Hops" detail view) always need a raw
  socket on every OS, because setting the TTL per-probe requires one. If hop
  data doesn't populate, the dashboard tells you directly ("Hop data needs
  elevated privileges").

**Prefer least privilege — don't reach for root unless you actually need hop
stats.** When you do need it:

| OS | Least-privilege way to enable hop stats |
|----|------------------------------------------|
| **Linux** | Grant the one capability, once — **no root needed at runtime**: `sudo setcap cap_net_raw+ep /path/to/NetPulse`, then run `./NetPulse` as your normal user. |
| **macOS** | Ping works without elevation. Hop stats need `sudo ./NetPulse`. |
| **Windows** | Ping works normally. For hop stats, right-click → *Run as administrator*. |

> **Why avoid `sudo` where you can:** running the whole app as root makes its
> database and data directory root-owned, which can cause a later non-root
> run to fail opening its own files. The Linux `setcap` approach sidesteps
> that entirely — the binary carries just the raw-socket capability and
> otherwise runs as you.

---

## Configuration

NetPulse reads `config.yaml` from, in order:

1. Your OS config directory (`platformdirs`):
   - Windows: `%APPDATA%\NetPulse\NetPulse\config.yaml`
   - macOS: `~/Library/Application Support/NetPulse/config.yaml`
   - Linux: `~/.config/NetPulse/config.yaml`
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

Data (the SQLite DB) is stored in your OS data directory — e.g.
`~/Library/Application Support/NetPulse/netpulse.db` on macOS.

---

## Building a standalone executable

Must be built natively on each target OS — PyInstaller does not
cross-compile. `.github/workflows/build.yml` runs a matrix build (Windows /
macOS / Linux) on every push and uploads all three artifacts; that's the
easiest way to get all three without owning all three machines.

To build locally for the current OS:

```bash
pip install pyinstaller
pyinstaller packaging/netpulse.spec --distpath dist --workpath build
```

Produces a single-file executable at `dist/NetPulse` (`dist/NetPulse.exe` on
Windows).

---

## Security

- **Every dependency is open source** (MIT / BSD / Apache / LGPL). Additions
  are vetted for license and known CVEs before inclusion — see
  `.claude/skills/dependency-security-audit/`. CI runs `pip-audit` against
  `requirements.txt` on every build.
- **No credential handling.** NetPulse never prompts for, receives, or stores
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
- **Chart.js is vendored locally** (`netpulse/static/js/vendor/`) rather than
  loaded from a CDN, so there's no live third-party script dependency and the
  app works fully offline.
