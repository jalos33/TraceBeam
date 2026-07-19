"""LAN monitoring engine — ping sampling, hop stats, MOS, and aggregation.

Uses icmplib (pure Python, no external ping/mtr/traceroute binaries) so
behavior is identical on Windows/macOS/Linux. Pure helpers here; scheduling
lives in ``netpulse.tasks`` and the HTTP surface in
``netpulse.routers.monitor``.

Permissions: raw ICMP sockets require elevated privileges on most platforms.
Ping alone can run unprivileged on macOS/Linux (icmplib falls back
automatically); hop-stats (traceroute) always needs a raw socket, since TTL
must be set per-probe. See README.md "Permissions" for per-OS setup
(``setcap`` on Linux, admin/sudo on macOS/Windows).
"""

from __future__ import annotations

import re
import socket
import statistics
from ipaddress import ip_address
from urllib.parse import urlparse

import icmplib

# ---------------------------------------------------------------------------
# Display window presets (label -> seconds)
# ---------------------------------------------------------------------------

WINDOW_SECONDS: dict[str, int] = {
    "5m": 5 * 60,
    "15m": 15 * 60,
    "30m": 30 * 60,
    "1h": 3600,
    "4h": 4 * 3600,
    "12h": 12 * 3600,
    "24h": 24 * 3600,
    "2d": 2 * 86400,
    "4d": 4 * 86400,
    "7d": 7 * 86400,
    "14d": 14 * 86400,
    "30d": 30 * 86400,
}

# Windows at/under this length are served from raw samples; longer windows use
# per-minute rollups.
RAW_WINDOW_MAX_SECONDS = 6 * 3600

_HOSTNAME_RE = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$"
)

PING_TIMEOUT = 2.0
TRACEROUTE_MAX_HOPS = 30


class TargetError(ValueError):
    """Raised when a target address is invalid."""


# ---------------------------------------------------------------------------
# Address parsing / validation
# ---------------------------------------------------------------------------

def parse_host(address: str) -> str:
    """Extract a probe-able host from an IP, hostname, or URL.

    Accepts ``8.8.8.8``, ``2001:4860:4860::8888``, ``example.com``,
    ``https://example.com/path``, ``example.com:8443``. Returns the bare host.
    Raises :class:`TargetError` on anything unsafe.
    """
    if not address or not address.strip():
        raise TargetError("Address cannot be empty")
    address = address.strip()

    # URL form -> take the hostname component.
    if "://" in address:
        parsed = urlparse(address)
        host = parsed.hostname or ""
    else:
        # Could still be host:port or [ipv6]:port
        host = address
        if host.startswith("[") and "]" in host:                 # [ipv6]:port
            host = host[1: host.index("]")]
        elif host.count(":") == 1 and "." in host.split(":")[0]:  # host:port (v4/fqdn)
            host = host.split(":")[0]

    host = host.strip()
    if not host:
        raise TargetError(f"Could not parse a host from: {address}")

    # Valid literal IP (v4 or v6)?
    try:
        ip_address(host)
        return host
    except ValueError:
        pass

    # Otherwise must be a safe hostname.
    if ".." in host or host.startswith(("-", "/")):
        raise TargetError(f"Invalid host: {host}")
    if _HOSTNAME_RE.match(host):
        return host
    raise TargetError(f"Invalid host: {host}")


def host_family(host: str, protocol: str) -> str:
    """Resolve the effective protocol (ipv4/ipv6) for a host given a preference.

    ``protocol`` is one of auto|ipv4|ipv6. For literal IPs the family is taken
    from the address; for hostnames the user preference wins (auto -> ipv4).
    """
    try:
        return "ipv6" if ip_address(host).version == 6 else "ipv4"
    except ValueError:
        pass
    if protocol in ("ipv4", "ipv6"):
        return protocol
    return "ipv4"


def _family_int(host: str, protocol: str) -> int:
    return 6 if host_family(host, protocol) == "ipv6" else 4


# ---------------------------------------------------------------------------
# Privilege detection
# ---------------------------------------------------------------------------

_ping_privileged: bool | None = None


def _detect_ping_privilege() -> bool:
    """Probe once whether raw ICMP sockets are available; cache the result.

    icmplib supports an unprivileged (SOCK_DGRAM) ping path on macOS/Linux
    when raw sockets aren't available. Windows has no such fallback.
    """
    global _ping_privileged
    if _ping_privileged is None:
        try:
            icmplib.ping("127.0.0.1", count=1, timeout=1, privileged=True)
            _ping_privileged = True
        except icmplib.SocketPermissionError:
            _ping_privileged = False
    return _ping_privileged


# ---------------------------------------------------------------------------
# Probing
# ---------------------------------------------------------------------------

def ping_once(host: str, protocol: str = "auto", timeout: float = PING_TIMEOUT) -> float | None:
    """Send a single ICMP echo. Returns RTT in ms, or ``None`` if lost."""
    try:
        result = icmplib.ping(
            host, count=1, timeout=timeout,
            family=_family_int(host, protocol),
            privileged=_detect_ping_privilege(),
        )
    except icmplib.ICMPLibError:
        return None
    return round(result.avg_rtt, 2) if result.is_alive else None


# Cache reverse-DNS lookups so repeated hop-stat runs stay cheap.
_rdns_cache: dict[str, str] = {}


def _rdns(ip: str) -> str:
    if ip in _rdns_cache:
        return _rdns_cache[ip]
    name = ip
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(1.0)
        name = socket.gethostbyaddr(ip)[0]
    except Exception:
        name = ip
    finally:
        socket.setdefaulttimeout(old_timeout)
    _rdns_cache[ip] = name
    return name


hop_stats_permission_denied = False  # set True once, for tasks.py to log a single warning


def run_hop_stats(host: str, protocol: str = "auto", cycles: int = 5) -> list[dict]:
    """Trace the path to ``host`` and return per-hop latency/loss stats.

    Equivalent to mtr's per-hop table: each hop is probed ``cycles`` times
    as the path is discovered via icmplib.traceroute. Always requires a raw
    socket (TTL must be set per-probe) — returns ``[]`` if unavailable.
    """
    global hop_stats_permission_denied
    try:
        hops = icmplib.traceroute(
            host, count=cycles, timeout=PING_TIMEOUT,
            family=_family_int(host, protocol),
            max_hops=TRACEROUTE_MAX_HOPS, privileged=True,
        )
    except icmplib.SocketPermissionError:
        hop_stats_permission_denied = True
        return []
    except icmplib.ICMPLibError:
        return []

    out: list[dict] = []
    for hop in hops:
        ip = hop.address or "???"
        name = _rdns(ip) if ip != "???" else ip
        rtts = hop.rtts  # raw per-probe RTTs (ms) for this hop
        out.append({
            "hop_no": hop.distance,
            "host": ip,
            "name": name,
            "loss_pct": round(hop.packet_loss * 100, 2),
            "sent": hop.packets_sent,
            "last_ms": round(rtts[-1], 2) if rtts else None,
            "avg_ms": round(hop.avg_rtt, 2) if hop.is_alive else None,
            "best_ms": round(hop.min_rtt, 2) if hop.is_alive else None,
            "worst_ms": round(hop.max_rtt, 2) if hop.is_alive else None,
            "stddev_ms": round(statistics.pstdev(rtts), 2) if len(rtts) > 1 else None,
        })
    return out


# ---------------------------------------------------------------------------
# Derived metrics
# ---------------------------------------------------------------------------

def compute_mos(avg_rtt: float | None, jitter: float | None, loss_pct: float) -> float | None:
    """Approximate MOS (1.0-5.0) from latency, jitter, and loss (ITU E-model).

    Returns ``None`` when there is no latency data (e.g. 100% loss).
    """
    if avg_rtt is None:
        return None
    jitter = jitter or 0.0
    # Effective latency folds in jitter and a fixed codec/handling delay.
    effective_latency = avg_rtt + jitter * 2 + 10.0
    if effective_latency < 160:
        r = 93.2 - (effective_latency / 40.0)
    else:
        r = 93.2 - (effective_latency - 120) / 10.0
    # Each 1% loss costs ~2.5 R-points.
    r -= loss_pct * 2.5
    if r < 0:
        return 1.0
    mos = 1 + 0.035 * r + r * (r - 60) * (100 - r) * 7e-6
    return round(max(1.0, min(5.0, mos)), 2)


def jitter_of(rtts: list[float]) -> float | None:
    """Mean absolute difference between consecutive RTTs."""
    if len(rtts) < 2:
        return 0.0 if rtts else None
    diffs = [abs(rtts[i] - rtts[i - 1]) for i in range(1, len(rtts))]
    return round(sum(diffs) / len(diffs), 2)


def bucket_stats(rtts_in_order: list[float | None]) -> dict:
    """Aggregate an ordered list of per-probe RTTs (None = lost) into stats."""
    sent = len(rtts_in_order)
    received_rtts = [r for r in rtts_in_order if r is not None]
    received = len(received_rtts)
    loss_pct = round((sent - received) / sent * 100, 2) if sent else 0.0

    if received:
        min_rtt = round(min(received_rtts), 2)
        max_rtt = round(max(received_rtts), 2)
        avg_rtt = round(sum(received_rtts) / received, 2)
    else:
        min_rtt = avg_rtt = max_rtt = None

    jitter = jitter_of(received_rtts)
    return {
        "sent": sent,
        "received": received,
        "loss_pct": loss_pct,
        "min_rtt": min_rtt,
        "avg_rtt": avg_rtt,
        "max_rtt": max_rtt,
        "jitter_ms": jitter,
        "mos": compute_mos(avg_rtt, jitter, loss_pct),
    }
