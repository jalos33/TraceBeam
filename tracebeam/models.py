"""SQLAlchemy models — continuous per-target LAN monitor."""

from datetime import datetime

from sqlalchemy import Boolean, Column, Integer, Float, String, DateTime, Index

from tracebeam.database import Base


class MonitorTarget(Base):
    """A user-managed monitoring target (IP, IPv6, or URL)."""

    __tablename__ = "monitor_targets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120))
    address = Column(String(255))          # raw user input (IP / hostname / URL)
    host = Column(String(255))             # resolved hostname/IP used for probing
    protocol = Column(String(10), default="auto")  # auto | ipv4 | ipv6
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.utcnow())


class PingSample(Base):
    """Raw per-probe ping result (short retention, ~48h)."""

    __tablename__ = "ping_samples"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.utcnow())
    rtt_ms = Column(Float, nullable=True)   # None == lost
    lost = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_ping_samples_target_ts", "target_id", "timestamp"),
    )


class PingRollup(Base):
    """Per-minute aggregate of ping samples (long retention, 30d+)."""

    __tablename__ = "ping_rollups"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, index=True)
    bucket = Column(DateTime(timezone=True))  # minute boundary (UTC)
    sent = Column(Integer, default=0)
    received = Column(Integer, default=0)
    loss_pct = Column(Float, default=0.0)
    min_rtt = Column(Float, nullable=True)
    avg_rtt = Column(Float, nullable=True)
    max_rtt = Column(Float, nullable=True)
    jitter_ms = Column(Float, nullable=True)
    mos = Column(Float, nullable=True)

    __table_args__ = (
        Index("ix_ping_rollups_target_bucket", "target_id", "bucket"),
    )


class HopStat(Base):
    """A single hop from the latest traceroute run for a target."""

    __tablename__ = "hop_stats"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, index=True)
    run_ts = Column(DateTime(timezone=True), default=lambda: datetime.utcnow())
    hop_no = Column(Integer)
    host = Column(String(255), nullable=True)   # IP
    name = Column(String(255), nullable=True)   # rDNS name (falls back to IP)
    loss_pct = Column(Float, default=0.0)
    sent = Column(Integer, default=0)
    last_ms = Column(Float, nullable=True)
    avg_ms = Column(Float, nullable=True)
    best_ms = Column(Float, nullable=True)
    worst_ms = Column(Float, nullable=True)
    stddev_ms = Column(Float, nullable=True)

    __table_args__ = (
        Index("ix_hop_stats_target_run", "target_id", "run_ts"),
    )
