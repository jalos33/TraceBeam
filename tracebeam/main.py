"""FastAPI app for the TraceBeam LAN monitor dashboard."""

from __future__ import annotations

import logging
import sys
import threading
import time
import webbrowser
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tracebeam import tasks
from tracebeam.config import get_config
from tracebeam.database import init_db
from tracebeam.routers import monitor

logger = logging.getLogger("tracebeam.main")
config = get_config()


def _static_dir() -> Path:
    """Resolve the bundled static dir, whether running from source or a
    PyInstaller-frozen executable (which unpacks to sys._MEIPASS)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "tracebeam" / "static"
    return Path(__file__).parent / "static"


STATIC_DIR = _static_dir()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    tasks.start_scheduler()
    try:
        yield
    finally:
        tasks.scheduler.shutdown()


app = FastAPI(title="TraceBeam LAN Monitor", lifespan=lifespan)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(monitor.router)


@app.get("/")
async def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


def _open_browser_when_ready(url: str, timeout: float = 10.0) -> None:
    """Poll the health endpoint in a background thread, then open the browser."""
    import urllib.request

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url + "/api/health", timeout=0.5)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.2)
    webbrowser.open(url)  # give up waiting, open anyway


def run() -> None:
    """Entry point for the packaged app: start the server and open a browser tab."""
    import uvicorn

    host = config["server"]["host"]
    port = config["server"]["port"]
    url = f"http://{host}:{port}"

    threading.Thread(target=_open_browser_when_ready, args=(url,), daemon=True).start()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run()
