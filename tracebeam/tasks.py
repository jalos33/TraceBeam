"""Background tasks for the TraceBeam LAN monitor (PingPlotter-style)."""

import asyncio
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from tracebeam.config import get_config, get_nested
from tracebeam.database import SessionLocal
from tracebeam.models import MonitorTarget, PingSample, PingRollup, HopStat
from tracebeam import monitor

logger = logging.getLogger("tracebeam.tasks")
config = get_config()
scheduler = AsyncIOScheduler()


def seed_targets_from_config():
    """Populate monitor_targets from config on first run (empty table only)."""
    db = SessionLocal()
    try:
        if db.execute(select(MonitorTarget.id).limit(1)).first():
            return
        entries = get_nested(config, "lan", "ping_targets", []) or []
        added = 0
        for entry in entries:
            if isinstance(entry, dict):
                name = entry.get("name") or entry.get("ipv4") or entry.get("ipv6")
                address = entry.get("ipv4") or entry.get("ipv6")
            else:
                name = address = str(entry)
            if not address:
                continue
            try:
                host = monitor.parse_host(address)
            except monitor.TargetError:
                continue
            db.add(MonitorTarget(
                name=name, address=address, host=host,
                protocol="auto", enabled=True, created_at=datetime.utcnow(),
            ))
            added += 1
        if added:
            db.commit()
            logger.info("Seeded %d monitor targets from config", added)
    except Exception:
        db.rollback()
        logger.exception("Failed to seed monitor targets")
    finally:
        db.close()


def _enabled_targets(db):
    return db.execute(
        select(MonitorTarget).where(MonitorTarget.enabled.is_(True))
    ).scalars().all()


async def periodic_lan_sample():
    """Ping every enabled target once, concurrently. Runs on a short interval."""
    try:
        db = SessionLocal()
        try:
            targets = [(t.id, t.host, t.protocol) for t in _enabled_targets(db)]
        finally:
            db.close()
        if not targets:
            return

        async def probe(host, protocol):
            return await asyncio.to_thread(monitor.ping_once, host, protocol)

        rtts = await asyncio.gather(*(probe(h, p) for _, h, p in targets))
        now = datetime.utcnow()

        db = SessionLocal()
        try:
            for (tid, _, _), rtt in zip(targets, rtts):
                db.add(PingSample(
                    target_id=tid, timestamp=now,
                    rtt_ms=rtt, lost=(rtt is None),
                ))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    except Exception as e:
        logger.exception("Error in periodic_lan_sample: %s", e)


async def periodic_lan_rollup():
    """Aggregate raw samples into per-minute rollups (idempotent)."""
    try:
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            # Process the last few fully-complete minutes (idempotent via existence check).
            current_min = now.replace(second=0, microsecond=0)
            buckets = [current_min - timedelta(minutes=i) for i in range(1, 6)]
            targets = [t.id for t in db.execute(select(MonitorTarget)).scalars().all()]

            for tid in targets:
                for bucket in buckets:
                    exists = db.execute(
                        select(PingRollup.id).where(
                            PingRollup.target_id == tid, PingRollup.bucket == bucket,
                        ).limit(1)
                    ).first()
                    if exists:
                        continue
                    samples = db.execute(
                        select(PingSample).where(
                            PingSample.target_id == tid,
                            PingSample.timestamp >= bucket,
                            PingSample.timestamp < bucket + timedelta(minutes=1),
                        ).order_by(PingSample.timestamp.asc())
                    ).scalars().all()
                    if not samples:
                        continue
                    stats = monitor.bucket_stats([s.rtt_ms for s in samples])
                    db.add(PingRollup(
                        target_id=tid, bucket=bucket,
                        sent=stats["sent"], received=stats["received"],
                        loss_pct=stats["loss_pct"], min_rtt=stats["min_rtt"],
                        avg_rtt=stats["avg_rtt"], max_rtt=stats["max_rtt"],
                        jitter_ms=stats["jitter_ms"], mos=stats["mos"],
                    ))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    except Exception as e:
        logger.exception("Error in periodic_lan_rollup: %s", e)


async def periodic_hop_stats():
    """Trace each enabled target and replace its stored hop stats."""
    try:
        cycles = int(get_nested(config, "lan", "mtr_cycles", 5))
        db = SessionLocal()
        try:
            targets = [(t.id, t.host, t.protocol) for t in _enabled_targets(db)]
        finally:
            db.close()

        for tid, host, protocol in targets:
            hops = await asyncio.to_thread(monitor.run_hop_stats, host, protocol, cycles)
            if not hops:
                if monitor.hop_stats_permission_denied:
                    logger.warning(
                        "Hop stats unavailable: raw ICMP sockets require elevated "
                        "privileges. See README.md 'Permissions'."
                    )
                continue
            run_ts = datetime.utcnow()
            db = SessionLocal()
            try:
                db.execute(
                    HopStat.__table__.delete().where(HopStat.target_id == tid)
                )
                for h in hops:
                    db.add(HopStat(
                        target_id=tid, run_ts=run_ts,
                        hop_no=h["hop_no"], host=h["host"], name=h["name"],
                        loss_pct=h["loss_pct"], sent=h["sent"],
                        last_ms=h["last_ms"], avg_ms=h["avg_ms"],
                        best_ms=h["best_ms"], worst_ms=h["worst_ms"],
                        stddev_ms=h["stddev_ms"],
                    ))
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
    except Exception as e:
        logger.exception("Error in periodic_hop_stats: %s", e)


async def prune_lan_data():
    """Enforce retention: raw samples ~48h, rollups N days, orphan hop stats."""
    try:
        raw_hours = int(get_nested(config, "lan", "raw_retention_hours", 48))
        retention_days = int(get_nested(config, "lan", "retention_days", 30))
        now = datetime.utcnow()
        raw_cutoff = now - timedelta(hours=raw_hours)
        rollup_cutoff = now - timedelta(days=retention_days)

        db = SessionLocal()
        try:
            db.execute(PingSample.__table__.delete().where(PingSample.timestamp < raw_cutoff))
            db.execute(PingRollup.__table__.delete().where(PingRollup.bucket < rollup_cutoff))
            # Drop hop stats for targets that no longer exist.
            live_ids = [t.id for t in db.execute(select(MonitorTarget)).scalars().all()]
            if live_ids:
                db.execute(HopStat.__table__.delete().where(HopStat.target_id.notin_(live_ids)))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    except Exception as e:
        logger.exception("Error in prune_lan_data: %s", e)


def start_scheduler():
    logger.info("Starting APScheduler with background tasks")

    seed_targets_from_config()

    sample_interval = int(get_nested(config, "lan", "sample_interval_seconds", 2))
    mtr_interval = int(get_nested(config, "lan", "mtr_interval_seconds", 45))

    # APScheduler 3.x: prevent overlap (max_instances) and merge missed runs
    # (coalesce). 'misfire_behavior' is a 4.x-only arg — do not add it.
    job_opts = dict(max_instances=1, coalesce=True, misfire_grace_time=30)

    scheduler.add_job(periodic_lan_sample, 'interval', seconds=sample_interval, id='lan_sample', **job_opts)
    scheduler.add_job(periodic_lan_rollup, 'interval', seconds=60, id='lan_rollup', **job_opts)
    scheduler.add_job(periodic_hop_stats, 'interval', seconds=mtr_interval, id='lan_hop_stats', **job_opts)
    scheduler.add_job(prune_lan_data, 'interval', minutes=30, id='lan_prune', **job_opts)

    scheduler.start()
    logger.info("Scheduler started successfully")


async def main_async():
    start_scheduler()
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        scheduler.shutdown()
        logger.info("TraceBeam scheduler shutting down")
