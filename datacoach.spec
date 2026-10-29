# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build definition for the Data Coach desktop app.

Build with: .venv\\Scripts\\python.exe -m PyInstaller --noconfirm --clean datacoach.spec
"""

import os

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

datas = [
    ("app.py", "."),
    ("assets", "assets"),
    (".streamlit/config.toml", ".streamlit"),
]
binaries = []
hiddenimports = [
    "core",
    "core.config",
    "core.db",
    "core.diagnostic",
    "core.llm",
    "core.prompts",
    "core.roadmap",
    "ui",
    "ui.onboarding",
    "ui.styles",
    "ui.pages",
    "ui.pages.today",
    "ui.pages.coach",
    "ui.pages.data_lab",
    "ui.pages.interview_room",
    "ui.pages.dashboard_coach",
    "ui.pages.job_tracker",
    "ui.pages.progress",
    "ui.pages.settings",
    "ui.pages.placeholders",
    "tkinter",
    "tkinter.messagebox",
    "tkinter.ttk",
]

# Streamlit ships static assets and reads its own metadata at runtime; the
# window shell and keyring resolve components dynamically as well.
for package in ("streamlit", "altair", "plotly", "pydeck", "webview", "keyring"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

hiddenimports += collect_submodules("keyring.backends")
hiddenimports += collect_submodules("google.genai")

for distribution in (
    "streamlit",
    "altair",
    "plotly",
    "pandas",
    "numpy",
    "pyarrow",
    "google-genai",
    "keyring",
    "pywebview",
    "pythonnet",
    "clr-loader",
):
    try:
        datas += copy_metadata(distribution)
    except Exception:
        pass

a = Analysis(
    ["desktop.py"],
    pathex=[os.getcwd()],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DataCoach",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
    version="version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="DataCoach",
)
