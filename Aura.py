"""Aura fast launcher — used by Desktop shortcut (pythonw Aura.py)."""

from __future__ import annotations

import atexit
import os
import socket
import subprocess
import sys
import time
import traceback
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("AURA_PORT", "8600"))
HOST = "127.0.0.1"
URL = f"http://{HOST}:{PORT}"
LOG_DIR = Path.home() / ".buddy"
LOG = LOG_DIR / "aura-launch.log"
ERR = LOG_DIR / "aura-backend.err"
ICON = ROOT / "Aura.ico"
LOCK = LOG_DIR / "aura-ui.lock"
READY_TIMEOUT = 25.0


def log(msg: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}\n")
    except Exception:
        pass


def port_open() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.2):
            return True
    except OSError:
        return False


def kill_port_listeners() -> None:
    if sys.platform != "win32":
        return
    flags = 0x08000000
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, errors="ignore", creationflags=flags)
    except Exception as e:
        log(f"netstat: {e}")
        return
    for line in out.splitlines():
        if f":{PORT}" in line and "LISTENING" in line:
            pid = line.split()[-1]
            if pid.isdigit() and int(pid) not in (0, os.getpid()):
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, creationflags=flags)
                log(f"killed listener pid={pid}")


def python_backend() -> str:
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        alt = exe.with_name("python.exe")
        if alt.is_file():
            return str(alt)
    return str(exe)


def acquire_ui_lock() -> bool:
    """Return False if another UI launcher is already active (and focus it)."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        try:
            age = time.time() - LOCK.stat().st_mtime
            old_pid = int(LOCK.read_text(encoding="utf-8").strip() or "0")
        except Exception:
            age, old_pid = 9999, 0
        # Stale lock > 60s, or dead process
        alive = False
        if old_pid and sys.platform == "win32":
            try:
                import ctypes
                SYNCHRONIZE = 0x00100000
                handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, old_pid)
                if handle:
                    ctypes.windll.kernel32.CloseHandle(handle)
                    alive = True
            except Exception:
                alive = False
        if alive and age < 120:
            log(f"another UI active pid={old_pid} — focusing")
            focus_aura_window()
            if port_open():
                # Also poke browser as visible fallback if window is stuck behind
                return False
            return False
        try:
            LOCK.unlink(missing_ok=True)
        except Exception:
            pass
    try:
        LOCK.write_text(str(os.getpid()), encoding="utf-8")
        atexit.register(lambda: LOCK.unlink(missing_ok=True))
    except Exception:
        pass
    return True


def focus_aura_window() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "Aura")
        if hwnd:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            log("focused existing Aura window")
    except Exception as e:
        log(f"focus failed: {e}")


def apply_hwnd_icon(icon_path: str) -> None:
    if sys.platform != "win32":
        return
    import ctypes
    user32 = ctypes.windll.user32
    WM_SETICON, ICON_SMALL, ICON_BIG = 0x0080, 0, 1
    IMAGE_ICON, LR_LOADFROMFILE = 1, 0x0010
    hwnd = user32.FindWindowW(None, "Aura")
    if not hwnd:
        return
    big = user32.LoadImageW(None, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
    small = user32.LoadImageW(None, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
    if big:
        user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, big)
    if small:
        user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small)


def start_backend() -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    flags = 0x08000000 if sys.platform == "win32" else 0
    ERR.parent.mkdir(parents=True, exist_ok=True)
    err_f = open(ERR, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [python_backend(), "-m", "buddy.code", "--host", HOST, "--port", str(PORT)],
        cwd=str(ROOT),
        env=env,
        creationflags=flags,
        stdout=err_f,
        stderr=subprocess.STDOUT,
    )
    log(f"backend pid={proc.pid} errlog={ERR}")
    return proc


def wait_ready(timeout: float = READY_TIMEOUT) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_open():
            return True
        time.sleep(0.12)
    return False


def open_desktop(url: str) -> bool:
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.aura.ide")
    except Exception:
        pass
    try:
        import webview
    except Exception as e:
        log(f"pywebview import failed: {e}")
        return False

    icon = str(ICON) if ICON.is_file() else None
    try:
        window = webview.create_window(
            title="Aura",
            url=url,
            width=1440,
            height=900,
            min_size=(960, 640),
            background_color="#11111b",
            text_select=True,
            focus=True,
        )

        def _on_shown():
            focus_aura_window()
            if icon:
                try:
                    apply_hwnd_icon(icon)
                except Exception as e:
                    log(f"icon: {e}")

        try:
            window.events.shown += _on_shown
        except Exception:
            pass

        log("webview.start …")
        if icon:
            webview.start(debug=False, icon=icon)
        else:
            webview.start(debug=False)
        log("webview closed")
        return True
    except Exception as e:
        log(f"webview failed: {e}\n{traceback.format_exc()}")
        return False


def alert(msg: str) -> None:
    if sys.platform != "win32":
        print(msg)
        return
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, "Aura", 0x40)
    except Exception:
        pass


def main() -> int:
    t0 = time.time()
    log(f"START py={sys.executable}")
    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    if not acquire_ui_lock():
        # Another UI owns the lock — try focus, else browser
        focus_aura_window()
        if port_open():
            webbrowser.open(URL)
        return 0

    # Always restart backend so code/static updates (terminal PTY, UI) actually load.
    # Reusing a stale listener was causing /ws/terminal → 403 (route missing).
    if port_open():
        log("stopping existing backend on port")
        kill_port_listeners()
        time.sleep(0.35)

    kill_port_listeners()
    proc = start_backend()
    if not wait_ready():
        err_txt = ""
        try:
            err_txt = ERR.read_text(encoding="utf-8", errors="ignore")[-1500:]
        except Exception:
            pass
        log(f"backend timeout; output:\n{err_txt}")
        alert(
            "Aura could not start the local server.\n\n"
            f"Details:\n{ERR}\n\n{err_txt[:500]}"
        )
        return 1
    log(f"ready in {time.time() - t0:.2f}s (backend pid ok)")
    if proc.poll() is not None:
        log(f"backend exited early code={proc.returncode}")
        alert("Aura backend exited immediately. See aura-backend.err for details.")
        return 1

    # Open desktop window (blocks). If it fails instantly, browser.
    if not open_desktop(URL):
        log("opening browser fallback")
        webbrowser.open(URL)
        alert("Opened Aura in your browser.\n(Install/fix pywebview for the desktop window.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
