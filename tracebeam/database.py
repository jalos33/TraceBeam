"""SQLAlchemy database setup."""

from pathlib import Path

from platformdirs import user_data_dir
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

_data_dir = Path(user_data_dir("TraceBeam", "TraceBeam"))
_data_dir.mkdir(parents=True, exist_ok=True)
DB_PATH = _data_dir / "tracebeam.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    """WAL lets reads happen while the scheduler writes (no reader lock-out),
    which keeps the dashboard snappy under continuous sampling."""
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Yield a DB session; closes it on exit.

    Deliberately a bare generator, NOT ``@contextmanager``-wrapped -- FastAPI's
    dependency cleanup calls ``.throw()`` on whatever this returns when an
    exception propagates, and a ``_GeneratorContextManager`` doesn't support
    that (surfaces as a 500 on every endpoint using this dependency).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    from tracebeam import models  # noqa: F401  (registers models on Base.metadata)
    Base.metadata.create_all(bind=engine)
