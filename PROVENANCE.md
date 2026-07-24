# TraceBeam — Origin & Provenance

This file documents where TraceBeam's code came from and how it was built. It
exists as a clear, dated record of independent creation, in case the project's
originality is ever questioned. See [`PATENT_ANALYSIS.md`](PATENT_ANALYSIS.md)
for the broader IP risk assessment.

## Lineage

TraceBeam began as a fork of the author's **own prior project, WiPie** —
specifically its "LAN Monitor" tab — rebuilt from a Raspberry-Pi-only appliance
into a standalone cross-platform (Windows/macOS/Linux) desktop app.

- **Author of both:** the same author owns WiPie and TraceBeam. TraceBeam
  derives only from the author's own earlier work — no third-party codebase.
- **What changed vs. WiPie:** WiPie ran as two separate systemd services (an API
  and a collector) sharing a database on a fixed Pi path, shelling out to the
  system `ping` and `mtr` binaries. TraceBeam is a single Python process
  (FastAPI + APScheduler + SQLite) that opens a local browser dashboard, with an
  OS-appropriate per-user data directory. The probing engine was **rewritten
  from scratch** around `icmplib` (see below).

## Independent implementation

TraceBeam was written against **public, open protocols and standards**, not by
copying, decompiling, or reimplementing any commercial product:

- **ICMP echo (ping)** — RFC 792 (1981).
- **TTL-based traceroute** — the technique introduced by Van Jacobson's
  `traceroute` (1987): increment the IP TTL per probe and read the returned
  ICMP "Time Exceeded". Implemented here via the open-source library
  [`icmplib`](https://github.com/ValentinBELYN/icmplib), used **unmodified**
  through its public API (`ping()`, `traceroute()`) from
  `tracebeam/monitor.py`.
- **Per-hop latency / loss / jitter tables** — the long-established model of
  `mtr` (1997) and `SmokePing` (~2000).
- **MOS / call-quality score** — a direct implementation of the published
  **ITU-T G.107 E-model** standard, in `compute_mos()` in
  `tracebeam/monitor.py`. This is a public formula; ITU reports no known
  blocking IP required to implement the Recommendation.

No source code, UI assets, help text, icons, or branding were taken from
PingPlotter or any other commercial network-monitoring product. Any conceptual
resemblance to such tools reflects shared, decades-old public prior art (ping,
traceroute, mtr, SmokePing), not derivation.

## A note on early wording

Some early drafts of this project described the dashboard as
"PingPlotter-style" — using a well-known product name as shorthand for the
*genre* of continuous latency-over-time graphing (the same category as the
open-source `mtr` and `SmokePing` tools). That wording was later reworded, in
the ordinary course of editing, to describe TraceBeam on its own terms. The
change was one of clarity and positioning; the earlier phrasing referred to a
category of tool, not to any borrowed code or design.

## Naming & branding

"TraceBeam" is an original name, chosen to be distinct from existing products.
The project does not use, imitate, or trade on the name, logo, color scheme,
icon, or trade dress of PingPlotter (a trademark of Pingman Tools LLC /
Nessoft LLC) or any other product.

## Licensing

TraceBeam is MIT-licensed (see [`LICENSE`](LICENSE)). Its full third-party
dependency closure and each package's license is documented in
[`NOTICE.md`](NOTICE.md). The only copyleft component anywhere in the
distribution is `icmplib` (LGPL-3.0), used unmodified via its public API, with
LGPL obligations satisfied as described in `NOTICE.md`.

---

*Dated record maintained by the project author. Not legal advice.*
