# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Ledgerline desktop backend (ledgerline-backend.exe).
# Run from the desktop/ folder on Windows:
#   pyinstaller --distpath resources\backend --workpath build\pyi-work backend.spec
import os

block_cipher = None
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(SPEC)), "..", "backend")

a = Analysis(
    [os.path.join(BACKEND_DIR, "desktop_entry.py")],
    pathex=[BACKEND_DIR],
    binaries=[],
    datas=[],
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
        "motor",
        "pymongo",
        "dns",
        "dns.resolver",
        "openpyxl",
        "reportlab.graphics.barcode",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "torch", "tensorflow"],
    noarchive=False,
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
    name="ledgerline-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
