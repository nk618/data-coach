"""Windows desktop entry point for Data Coach.

Default mode opens the app in a native WebView2 window. The Streamlit server
runs as a child process of this same executable, which is what lets the frozen
build ship as one ``DataCoach.exe`` with no Python install required.

Server mode (``--server --port N``) runs the Streamlit server itself.
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

FROZEN = bool(getattr(sys, "frozen", False))
BUNDLE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
TITLE = "Data Coach"
WINDOW_TITLE = "Data Coach — 21-Day Data Analyst Sprint"
MIN_PORT = 8765
PORT_SCAN = 40


def _default_data_dir() -> Path:
    override = os.environ.get("DATACOACH_DATA_DIR")
    if override:
        return Path(override)
    if FROZEN:
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "DataCoach"
    return BUNDLE / "data"


DATA_DIR = _default_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = DATA_DIR / "app.log"
SERVER_FILE = DATA_DIR / "server.json"


def log(message: str) -> None:
    try:
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}\n")
    except Exception:
        pass


def _attach_streams() -> None:
    """Windowed builds have no std handles; give logging and uvicorn a sink."""
    if sys.stdout is None or sys.stderr is None:
        try:
            handle = LOG_PATH.open("a", encoding="utf-8", buffering=1)
        except Exception:
            handle = open(os.devnull, "w", encoding="utf-8")
        if sys.stdout is None:
            sys.stdout = handle
        if sys.stderr is None:
            sys.stderr = handle
    if sys.stdin is None:
        try:
            sys.stdin = open(os.devnull, "r", encoding="utf-8")
        except Exception:
            pass


def show_error(message: str, detail_path: Path | None = None) -> None:
    log(message)
    text = message
    if detail_path:
        text += f"\n\nLog: {detail_path}"
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


def free_port() -> int:
    for port in range(MIN_PORT, MIN_PORT + PORT_SCAN):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port available for the local server.")


def wait_for_server(port: int, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if health_check(port):
            return True
        time.sleep(0.4)
    return False


def spawn_server(port: int) -> subprocess.Popen:
    if FROZEN:
        command = [sys.executable, "--server", "--port", str(port)]
    else:
        python = Path(sys.executable)
        pythonw = python.with_name("pythonw.exe")
        executable = pythonw if pythonw.exists() else python
        command = [
            str(executable),
            str(Path(__file__).resolve()),
            "--server",
            "--port",
            str(port),
        ]

    log_handle = LOG_PATH.open("a", encoding="utf-8", buffering=1)
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    log(f"Starting server: {' '.join(command)}")
    return subprocess.Popen(
        command,
        cwd=str(BUNDLE),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=flags,
        env={**os.environ, "DATACOACH_DATA_DIR": str(DATA_DIR)},
    )


def run_server(port: int) -> None:
    _attach_streams()
    os.chdir(BUNDLE)
    os.environ.setdefault("DATACOACH_DATA_DIR", str(DATA_DIR))

    sys.argv = [
        "streamlit",
        "run",
        str(BUNDLE / "app.py"),
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
        "--global.developmentMode",
        "false",
    ]

    from streamlit.web import cli as stcli

    log(f"Streamlit server starting on port {port}")
    sys.exit(stcli.main())


def browser_fallback(url: str, process: subprocess.Popen | None) -> None:
    webbrowser.open(url)
    try:
        import tkinter as tk
        from tkinter import ttk

        root = tk.Tk()
        root.title(TITLE)
        root.geometry("400x180")
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
        if process is not None:
            process.wait()


def terminate(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=8)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def run_window(browser_only: bool = False) -> None:
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "DataCoach.Desktop"
            )
        except Exception:
            pass

    log(f"Starting Data Coach (frozen={FROZEN}, bundle={BUNDLE}, data={DATA_DIR})")

    existing = existing_server()
    process: subprocess.Popen | None = None
    owns_server = False
    port: int

    if existing:
        port = existing
        log(f"Reusing running server on port {port}")
    else:
        try:
            port = free_port()
        except RuntimeError as exc:
            show_error(str(exc))
            return
        process = spawn_server(port)
        owns_server = True
        if not wait_for_server(port):
            log("Server did not become healthy in time")
            terminate(process)
            show_error("Data Coach could not start its local server.", LOG_PATH)
            return
        SERVER_FILE.write_text(
            json.dumps({"port": port, "pid": os.getpid()}), encoding="utf-8"
        )

    url = f"http://127.0.0.1:{port}"

    try:
        if browser_only:
            raise RuntimeError("browser mode requested")
        import webview

        log(f"Opening native window at {url}")
        webview.create_window(
            WINDOW_TITLE,
            url,
            width=1480,
            height=940,
            min_size=(1080, 720),
            text_select=True,
        )
        webview.start()
    except Exception as exc:
        log(f"Native window unavailable: {exc}")
        browser_fallback(url, process)
    finally:
        if owns_server:
            try:
                SERVER_FILE.unlink()
            except Exception:
                pass
        terminate(process)
        log("Data Coach closed")


def main() -> None:
    args = sys.argv[1:]
    if "--server" in args:
        try:
            port = int(args[args.index("--port") + 1])
        except (ValueError, IndexError):
            port = MIN_PORT
        run_server(port)
        return
    run_window(browser_only="--browser" in args)


if __name__ == "__main__":
    main()
