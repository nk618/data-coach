"""Launch Data Coach in a native desktop window.

Started by Start Data Coach.bat / the desktop shortcut using the project's
virtual environment (pythonw.exe, so no console window appears).
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LOG_PATH = DATA_DIR / "launcher.log"
SERVER_FILE = DATA_DIR / "server.json"
TITLE = "Data Coach"


def log(message: str) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}\n")
    except Exception:
        pass


def show_error(message: str, detail_path: Path | None = None) -> None:
    log(message)
    text = message
    if detail_path:
        text += f"\n\nDetails: {detail_path}"
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(TITLE, text)
        root.destroy()
    except Exception:
        pass


def health_check(port: int, timeout: float = 0.8) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/_stcore/health", timeout=timeout
        ) as response:
            return response.status == 200
    except Exception:
        return False


def existing_server() -> int | None:
    if not SERVER_FILE.exists():
        return None
    try:
        info = json.loads(SERVER_FILE.read_text(encoding="utf-8"))
        port = int(info["port"])
        if health_check(port):
            return port
    except Exception:
        pass
    return None


def free_port(start: int = 8765) -> int:
    for port in range(start, start + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port available for the local server.")


def wait_for_server(port: int, timeout: float = 45.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if health_check(port):
            return True
        time.sleep(0.4)
    return False


def check_dependencies() -> list[str]:
    missing = []
    for module, label in [
        ("streamlit", "streamlit"),
        ("google.genai", "google-genai"),
        ("pandas", "pandas"),
        ("plotly", "plotly"),
        ("webview", "pywebview"),
        ("keyring", "keyring"),
    ]:
        try:
            __import__(module)
        except Exception:
            missing.append(label)
    return missing


def browser_fallback(url: str, process: subprocess.Popen) -> None:
    webbrowser.open(url)
    try:
        import tkinter as tk
        from tkinter import ttk

        root = tk.Tk()
        root.title(TITLE)
        root.geometry("380x170")
        root.attributes("-topmost", True)
        ttk.Label(
            root,
            text="Data Coach is open in your browser.",
            font=("Segoe UI", 10, "bold"),
            padding=(16, 16, 16, 4),
        ).pack()
        ttk.Label(
            root,
            text="Close this window to stop the local app.",
            padding=(16, 0, 16, 10),
        ).pack()
        ttk.Button(root, text="Stop Data Coach", command=root.destroy).pack(pady=8)
        root.protocol("WM_DELETE_WINDOW", root.destroy)
        root.mainloop()
    except Exception:
        process.wait()


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "DataCoach.Desktop"
            )
        except Exception:
            pass

    missing = check_dependencies()
    if missing:
        show_error(
            "Data Coach is missing required packages:\n\n"
            + ", ".join(missing)
            + '\n\nRun "Setup Data Coach.bat" once, then try again.'
        )
        return

    existing = existing_server()
    process: subprocess.Popen | None = None
    owns_server = False

    if existing:
        port = existing
        log(f"Reusing running server on port {port}")
    else:
        port = free_port()
        streamlit_log = DATA_DIR / "streamlit.log"
        log_handle = streamlit_log.open("a", encoding="utf-8", buffering=1)
        command = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(ROOT / "app.py"),
            "--server.address",
            "127.0.0.1",
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--server.fileWatcherType",
            "none",
            "--browser.gatherUsageStats",
            "false",
        ]
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        process = subprocess.Popen(
            command,
            cwd=str(ROOT),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
        owns_server = True
        if not wait_for_server(port):
            log("Streamlit failed to start; see streamlit.log")
            try:
                process.terminate()
            except Exception:
                pass
            show_error(
                "Data Coach could not start its local server.",
                streamlit_log,
            )
            return
        SERVER_FILE.write_text(
            json.dumps({"port": port, "pid": os.getpid()}), encoding="utf-8"
        )

    url = f"http://127.0.0.1:{port}"

    try:
        import webview

        log(f"Opening native window at {url}")
        webview.create_window(
            "Data Coach — 21-Day Data Analyst Sprint",
            url,
            width=1480,
            height=940,
            min_size=(1080, 720),
        )
        webview.start()
    except Exception as exc:
        log(f"Native window failed: {exc}")
        if process is not None:
            browser_fallback(url, process)
        else:
            webbrowser.open(url)
    finally:
        if owns_server:
            try:
                SERVER_FILE.unlink()
            except Exception:
                pass
        if process is not None and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=8)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        log("Data Coach closed")


if __name__ == "__main__":
    main()
