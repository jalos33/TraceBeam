"""LAN monitor API — target CRUD, summary, per-target series, and hop stats."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from netpulse import monitor
from netpulse.database import get_db
from netpulse.models import MonitorTarget, PingSample, PingRollup, HopStat

router = APIRouter(prefix="/api/monitor", tags=["monitor"])

MAX_TARGETS = 32
SUMMARY_SPARK_POINTS = 200   # feeds both the row sparkline and the stacked strips
DETAIL_MAX_POINTS = 800


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class TargetCreate(BaseModel):
    name: str | None = None
    address: str
    protocol: str = "auto"


class TargetUpdate(BaseModel):
    name: str | None = None
    protocol: str | None = None
    enabled: bool | None = None


def _validate_protocol(protocol: str) -> str:
    if protocol not in ("auto", "ipv4", "ipv6"):
        raise HTTPException(status_code=400, detail="protocol must be auto, ipv4, or ipv6")
    return protocol


def _target_dict(t: MonitorTarget) -> dict:
    return {
        "id": t.id, "name": t.name, "address": t.address, "host": t.host,
        "protocol": t.protocol, "enabled": t.enabled,
    }


# ---------------------------------------------------------------------------
# Window / series helpers
# ---------------------------------------------------------------------------

def _downsample(points: list[dict], n: int) -> list[dict]:
    """Reduce points to ~n contiguous buckets, preserving loss and min/max."""
    if len(points) <= n:
        return points
    out: list[dict] = []
    step = len(points) / n
    for i in range(n):
        group = points[int(i * step): int((i + 1) * step)]
        if not group:
            continue
        rtts = [p["rtt"] for p in group if p["rtt"] is not None]
        mins = [p["min"] for p in group if p.get("min") is not None]
        maxs = [p["max"] for p in group if p.get("max") is not None]
        out.append({
            "t": group[0]["t"],
            "rtt": round(sum(rtts) / len(rtts), 2) if rtts else None,
            "min": round(min(mins), 2) if mins else None,
            "max": round(max(maxs), 2) if maxs else None,
            "loss": round(sum(p["loss"] for p in group) / len(group), 3),
        })
    return out


def _window_data(db: Session, target_id: int, window: str, max_points: int) -> dict:
    """Return aggregate stats + a (downsampled) rtt/loss series for a target."""
    secs = monitor.WINDOW_SECONDS.get(window, 3600)
    since = datetime.utcnow() - timedelta(seconds=secs)

    if secs <= monitor.RAW_WINDOW_MAX_SECONDS:
        rows = db.execute(
            select(PingSample).where(
                PingSample.target_id == target_id, PingSample.timestamp >= since,
            ).order_by(PingSample.timestamp.asc())
        ).scalars().all()
        points = [{
            "t": r.timestamp.isoformat() + "Z", "rtt": r.rtt_ms,
            "min": r.rtt_ms, "max": r.rtt_ms, "loss": 1.0 if r.lost else 0.0,
        } for r in rows]
        rtts_ordered = [r.rtt_ms for r in rows if r.rtt_ms is not None]
        sent = len(rows)
        received = len(rtts_ordered)
        cur = next((r.rtt_ms for r in reversed(rows) if r.rtt_ms is not None), None)
        min_rtt = round(min(rtts_ordered), 2) if rtts_ordered else None
        max_rtt = round(max(rtts_ordered), 2) if rtts_ordered else None
        avg_rtt = round(sum(rtts_ordered) / received, 2) if received else None
        jitter = monitor.jitter_of(rtts_ordered)
    else:
        rows = db.execute(
            select(PingRollup).where(
                PingRollup.target_id == target_id, PingRollup.bucket >= since,
            ).order_by(PingRollup.bucket.asc())
        ).scalars().all()
        points = [{
            "t": r.bucket.isoformat() + "Z", "rtt": r.avg_rtt,
            "min": r.min_rtt, "max": r.max_rtt,
            "loss": (r.loss_pct or 0.0) / 100.0,
        } for r in rows]
        sent = sum(r.sent or 0 for r in rows)
        received = sum(r.received or 0 for r in rows)
        avgs = [(r.avg_rtt, r.received or 0) for r in rows if r.avg_rtt is not None and r.received]
        avg_rtt = round(sum(a * w for a, w in avgs) / sum(w for _, w in avgs), 2) if avgs else None
        mins = [r.min_rtt for r in rows if r.min_rtt is not None]
        maxs = [r.max_rtt for r in rows if r.max_rtt is not None]
        min_rtt = round(min(mins), 2) if mins else None
        max_rtt = round(max(maxs), 2) if maxs else None
        cur = next((r.avg_rtt for r in reversed(rows) if r.avg_rtt is not None), None)
        jits = [r.jitter_ms for r in rows if r.jitter_ms is not None]
        jitter = round(sum(jits) / len(jits), 2) if jits else None

    loss_pct = round((sent - received) / sent * 100, 2) if sent else 0.0
    mos = monitor.compute_mos(avg_rtt, jitter, loss_pct)

    return {
        "count": sent,
        "err": sent - received,
        "cur": cur,
        "avg": avg_rtt,
        "min": min_rtt,
        "max": max_rtt,
        "jitter": jitter,
        "loss_pct": loss_pct,
        "mos": mos,
        "series": _downsample(points, max_points),
    }


# ---------------------------------------------------------------------------
# Targets CRUD
# ---------------------------------------------------------------------------

@router.get("/targets")
def list_targets(db: Session = Depends(get_db)):
    targets = db.execute(select(MonitorTarget).order_by(MonitorTarget.id.asc())).scalars().all()
    return {"targets": [_target_dict(t) for t in targets]}


@router.post("/targets")
def create_target(body: TargetCreate, db: Session = Depends(get_db)):
    count = db.execute(select(MonitorTarget.id)).scalars().all()
    if len(count) >= MAX_TARGETS:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_TARGETS} targets reached")
    _validate_protocol(body.protocol)
    try:
        host = monitor.parse_host(body.address)
    except monitor.TargetError as e:
        raise HTTPException(status_code=400, detail=str(e))

    target = MonitorTarget(
        name=(body.name or body.address).strip(),
        address=body.address.strip(),
        host=host,
        protocol=body.protocol,
        enabled=True,
        created_at=datetime.utcnow(),
    )
    db.add(target)
    try:
        db.commit()
        db.refresh(target)
    except Exception:
        db.rollback()
        raise
    return {"success": True, "target": _target_dict(target)}


@router.patch("/targets/{target_id}")
def update_target(target_id: int, body: TargetUpdate, db: Session = Depends(get_db)):
    target = db.get(MonitorTarget, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    if body.name is not None:
        target.name = body.name.strip()
    if body.protocol is not None:
        target.protocol = _validate_protocol(body.protocol)
    if body.enabled is not None:
        target.enabled = body.enabled
    try:
        db.commit()
        db.refresh(target)
    except Exception:
        db.rollback()
        raise
    return {"success": True, "target": _target_dict(target)}


@router.delete("/targets/{target_id}")
def delete_target(target_id: int, db: Session = Depends(get_db)):
    target = db.get(MonitorTarget, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    db.execute(PingSample.__table__.delete().where(PingSample.target_id == target_id))
    db.execute(PingRollup.__table__.delete().where(PingRollup.target_id == target_id))
    db.execute(HopStat.__table__.delete().where(HopStat.target_id == target_id))
    db.delete(target)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"success": True}


# ---------------------------------------------------------------------------
# Summary / series / hops
# ---------------------------------------------------------------------------

@router.get("/summary")
def summary(window: str = Query("1h"), db: Session = Depends(get_db)):
    """All targets with aggregate stats + a sparkline series over the window."""
    targets = db.execute(select(MonitorTarget).order_by(MonitorTarget.id.asc())).scalars().all()
    rows = []
    for t in targets:
        data = _window_data(db, t.id, window, SUMMARY_SPARK_POINTS)
        rows.append({**_target_dict(t), **data})
    return {"window": window, "targets": rows}


@router.get("/targets/{target_id}/series")
def target_series(
    target_id: int,
    window: str = Query("1h"),
    db: Session = Depends(get_db),
):
    target = db.get(MonitorTarget, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    data = _window_data(db, target_id, window, DETAIL_MAX_POINTS)
    return {"window": window, "target": _target_dict(target), **data}


@router.get("/targets/{target_id}/hops")
def target_hops(target_id: int, db: Session = Depends(get_db)):
    target = db.get(MonitorTarget, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    hops = db.execute(
        select(HopStat).where(HopStat.target_id == target_id).order_by(HopStat.hop_no.asc())
    ).scalars().all()
    run_ts = hops[0].run_ts.isoformat() + "Z" if hops else None
    return {
        "target": _target_dict(target),
        "run_ts": run_ts,
        "permission_denied": monitor.hop_stats_permission_denied,
        "hops": [{
            "hop_no": h.hop_no, "host": h.host, "name": h.name,
            "loss_pct": h.loss_pct, "sent": h.sent, "last_ms": h.last_ms,
            "avg_ms": h.avg_ms, "best_ms": h.best_ms, "worst_ms": h.worst_ms,
            "stddev_ms": h.stddev_ms,
        } for h in hops],
    }
