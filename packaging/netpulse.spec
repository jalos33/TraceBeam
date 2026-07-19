# PyInstaller spec — builds a single-file NetPulse executable.
# Run from the repo root: pyinstaller packaging/netpulse.spec
#
# Must be run natively on each target OS (Windows/macOS/Linux) — PyInstaller
# does not cross-compile. See .github/workflows/build.yml for a matrix build
# that produces all three from CI.

import sys
from pathlib import Path

block_cipher = None
repo_root = Path.cwd()

a = Analysis(
    [str(repo_root / "entrypoint.py")],
    pathex=[str(repo_root)],
    binaries=[],
    datas=[
        (str(repo_root / "netpulse" / "static"), "netpulse/static"),
        (str(repo_root / "config.yaml"), "."),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="NetPulse",
    debug=False,
    strip=False,
    upx=False,       # UPX-packed executables trip more AV heuristics; skip it
    console=True,     # keep a console/terminal window so scheduler logs are visible
    onefile=True,
)
