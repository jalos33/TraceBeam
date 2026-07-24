# TraceBeam — Deployment & Security Posture (for IT / security reviewers)

A concise reference for organizations evaluating TraceBeam for internal use.
See [`NOTICE.md`](NOTICE.md) for licensing and [`PROVENANCE.md`](PROVENANCE.md)
for project origin.

## What it is
A single local process (Python/FastAPI) that continuously pings a list of
targets and serves a dashboard in your browser at `127.0.0.1`. No cloud
service, no account, no external backend.

## Network & data behavior
| Question | Answer |
|---|---|
| Outbound telemetry / phone-home? | **None.** No analytics, no update check, no external calls. |
| Works fully offline? | **Yes.** Chart.js is vendored locally; no CDN or runtime fetch. |
| What network traffic does it generate? | ICMP echo (ping) and, if enabled, ICMP/UDP traceroute to the targets **you** configure. Nothing else. |
| What data is stored, and where? | A local SQLite DB (per-user OS data dir): target names, RTT numbers, timestamps, and network-hop IPs/hostnames. **No credentials, no payloads.** |
| Data retention | Raw samples ~48h, per-minute rollups ~30 days (both configurable), auto-pruned. |

## Access & exposure
- **Binds to `127.0.0.1` by default** — single-user, local only.
- **No authentication layer.** Setting `server.host: 0.0.0.0` exposes an
  **unauthenticated** dashboard to the network. Do not do this on an untrusted
  network without putting your own auth/reverse-proxy in front.

## Privileges
- **Ping-only monitoring** runs unprivileged on macOS/Linux.
- **Per-hop route stats (traceroute)** require raw ICMP sockets → elevated
  privileges on every OS (`setcap` on Linux, admin/sudo on macOS/Windows).
  This is inherent to traceroute, not specific to TraceBeam.
- Expect endpoint security/EDR tooling to notice raw-socket use; whitelist as
  appropriate.

## Supply chain
- All dependencies are open source; the only copyleft component is `icmplib`
  (LGPL-3.0, unmodified) — see [`NOTICE.md`](NOTICE.md) for the
  internal-use/redistribution analysis.
- Every tagged release ships a **CycloneDX SBOM** (`sbom.cdx.json`).
- CI is `pip-audit`-gated for known CVEs; builds are reproducible from source.
- Prebuilt binaries are **not code-signed** (Gatekeeper/SmartScreen will warn);
  organizations preferring signed artifacts can build from source in their own
  CI.

## Warranty
TraceBeam is provided under the MIT License, **"AS IS", without warranty or
indemnity**. Organizations adopting it do so under their own risk assessment.
