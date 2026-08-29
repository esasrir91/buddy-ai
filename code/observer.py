"""Aura Observer - a privacy-first, always-learning screen companion.

When the user opts in, the Observer periodically captures the screen, asks a
vision model "what is the user doing?", and appends a short text summary to a
local activity journal. The coding agent can then *recall* this context
("what was I working on?", "what errors keep recurring?"), so Aura keeps
learning while you work.

PRIVACY IS THE DEFAULT, NOT AN OPTION:
- Disabled by default. Nothing is captured until the user explicitly enables it.
- 100% local: screenshots are processed in-memory and DISCARDED by default
  (raw images are only kept on disk if the user turns that on).
- Only short text summaries are stored, in the user's home dir.
- Secret redaction scrubs things like API keys / tokens from summaries.
- Exclusion list: when a matching app/window is focused, capture is skipped.
- Pause/resume and one-click "clear all data" are always available.
"""

from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

_OBS_DIR = Path.home() / ".buddy" / "aura_observer"
_CONFIG_PATH = _OBS_DIR / "config.json"
_JOURNAL_PATH = _OBS_DIR / "journal.jsonl"

# Patterns scrubbed from summaries before they're ever written to disk.
_SECRET_PATTERNS = [
    re.compile(r"(?i)\b(sk|pk|rk)-[A-Za-z0-9]{16,}\b"),            # OpenAI-style keys
    re.compile(r"(?i)\bAKIA[0-9A-Z]{16}\b"),                        # AWS access key id
    re.compile(r"(?i)\bghp_[A-Za-z0-9]{20,}\b"),                    # GitHub token
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*\S+"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),  # emails
    re.compile(r"\b(?:\d[ -]*?){13,16}\b"),                          # card-ish numbers
]

DEFAULT_VISION_PROMPT = (
    "Look at this screenshot of a developer's screen. In ONE or TWO short sentences, "
    "describe what they appear to be working on: the app/tool in focus, the task, the "
    "programming language or file type if visible, and any visible error messages. "
    "Do NOT transcribe secrets, passwords, tokens, or personal data. Be concise."
)


class ObserverConfig(BaseModel):
    enabled: bool = False
    interval_seconds: int = Field(default=120, ge=15)
    store_screenshots: bool = False  # keep raw images on disk (off by default)
    redact_secrets: bool = True
    excluded_keywords: List[str] = Field(
        default_factory=lambda: ["password", "bank", "incognito", "private", "1password", "bitwarden", "keepass"]
    )
    max_journal_entries: int = 5000
    vision_prompt: str = DEFAULT_VISION_PROMPT


def load_config() -> ObserverConfig:
    if _CONFIG_PATH.exists():
        try:
            return ObserverConfig(**json.loads(_CONFIG_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass
    return ObserverConfig()


def save_config(cfg: ObserverConfig) -> None:
    _OBS_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(cfg.model_dump_json(indent=2), encoding="utf-8")


@dataclass
class JournalEntry:
    ts: str
    summary: str
    app: Optional[str] = None
    source: str = "vision"  # vision | ocr | window

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _redact(text: str) -> str:
    for pat in _SECRET_PATTERNS:
        text = pat.sub("[redacted]", text)
    return text


def _active_window_title() -> Optional[str]:
    """Best-effort focused-window title; returns None if unavailable."""
    try:
        import pygetwindow as gw  # type: ignore

        w = gw.getActiveWindow()
        if w:
            return getattr(w, "title", None) or None
    except Exception:
        pass
    return None


class ScreenObserver:
    """Background screen-learning loop. Thread-safe start/stop/pause."""

    def __init__(self, settings_provider) -> None:
        # settings_provider() -> CodeSettings (for the vision model + keys)
        self._settings_provider = settings_provider
        self.config = load_config()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._paused = False
        self._lock = threading.Lock()
        self.last_error: Optional[str] = None
        self.last_capture_ts: Optional[str] = None
        self._captures = 0

    # ------------------------------------------------------------- lifecycle
    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "paused": self._paused,
            "enabled": self.config.enabled,
            "captures": self._captures,
            "last_capture_ts": self.last_capture_ts,
            "last_error": self.last_error,
            "capture_available": _capture_available(),
            "interval_seconds": self.config.interval_seconds,
            "store_screenshots": self.config.store_screenshots,
        }

    def start(self) -> Dict[str, Any]:
        if not _capture_available():
            return {"ok": False, "error": "Screen capture needs `mss` + `pillow`. Install: pip install buddy-ai[observer]"}
        with self._lock:
            self.config.enabled = True
            save_config(self.config)
            if self.running:
                self._paused = False
                return {"ok": True, "status": self.status()}
            self._stop.clear()
            self._paused = False
            self._thread = threading.Thread(target=self._loop, name="aura-observer", daemon=True)
            self._thread.start()
        return {"ok": True, "status": self.status()}

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            self.config.enabled = False
            save_config(self.config)
            self._stop.set()
        return {"ok": True, "status": self.status()}

    def pause(self, paused: bool = True) -> Dict[str, Any]:
        self._paused = paused
        return {"ok": True, "status": self.status()}

    def update_config(self, patch: Dict[str, Any]) -> ObserverConfig:
        data = self.config.model_dump()
        data.update({k: v for k, v in patch.items() if v is not None})
        self.config = ObserverConfig(**data)
        save_config(self.config)
        return self.config

    # ---------------------------------------------------------------- worker
    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                if not self._paused:
                    self._tick()
            except Exception as exc:  # noqa: BLE001
                self.last_error = str(exc)
            # Sleep in small slices so stop() is responsive.
            slept = 0.0
            interval = max(15, self.config.interval_seconds)
            while slept < interval and not self._stop.is_set():
                time.sleep(1.0)
                slept += 1.0

    def _tick(self) -> None:
        title = _active_window_title()
        if title and self._is_excluded(title):
            return  # respect privacy exclusions

        png_bytes = _grab_screen_png()
        if not png_bytes:
            return

        summary, source = self._summarize(png_bytes, title)
        if not summary:
            summary, source = (title or "Active session", "window")

        if self.config.redact_secrets:
            summary = _redact(summary)

        entry = JournalEntry(ts=_now(), summary=summary.strip(), app=title, source=source)
        self._append(entry)
        self._captures += 1
        self.last_capture_ts = entry.ts
        self.last_error = None

        if self.config.store_screenshots:
            shot_dir = _OBS_DIR / "screenshots"
            shot_dir.mkdir(parents=True, exist_ok=True)
            (shot_dir / f"{entry.ts.replace(':', '-')}.png").write_bytes(png_bytes)
        # else: png_bytes is simply discarded (never written to disk)

    def _is_excluded(self, title: str) -> bool:
        low = title.lower()
        return any(kw.lower() in low for kw in self.config.excluded_keywords)

    def _summarize(self, png_bytes: bytes, title: Optional[str]) -> tuple[Optional[str], str]:
        # 1) Try a vision model (BYO-key) for a rich summary.
        try:
            text = _vision_summary(png_bytes, self._settings_provider(), self.config.vision_prompt)
            if text:
                return text, "vision"
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"vision: {exc}"
        # 2) Fall back to local OCR if available.
        try:
            ocr = _ocr_text(png_bytes)
            if ocr:
                return ("On screen: " + ocr[:280]), "ocr"
        except Exception:
            pass
        # 3) Give up on content; the caller will store the window title.
        return None, "window"

    # --------------------------------------------------------------- journal
    def _append(self, entry: JournalEntry) -> None:
        _OBS_DIR.mkdir(parents=True, exist_ok=True)
        with self._JLOCK:
            with _JOURNAL_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        self._trim()

    _JLOCK = threading.Lock()

    def _trim(self) -> None:
        try:
            lines = _JOURNAL_PATH.read_text(encoding="utf-8").splitlines()
            if len(lines) > self.config.max_journal_entries:
                keep = lines[-self.config.max_journal_entries :]
                _JOURNAL_PATH.write_text("\n".join(keep) + "\n", encoding="utf-8")
        except Exception:
            pass


# --------------------------------------------------------------- journal API
def read_journal(limit: int = 200, query: Optional[str] = None) -> List[Dict[str, Any]]:
    if not _JOURNAL_PATH.exists():
        return []
    entries: List[Dict[str, Any]] = []
    for line in _JOURNAL_PATH.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        if query and query.lower() not in (e.get("summary", "") + " " + (e.get("app") or "")).lower():
            continue
        entries.append(e)
    return entries[-limit:]


def clear_journal() -> bool:
    removed = False
    if _JOURNAL_PATH.exists():
        _JOURNAL_PATH.unlink()
        removed = True
    shots = _OBS_DIR / "screenshots"
    if shots.exists():
        for p in shots.glob("*.png"):
            p.unlink()
    return removed


def insights() -> Dict[str, Any]:
    """Lightweight aggregates over the journal (no LLM call)."""
    entries = read_journal(limit=100000)
    apps: Dict[str, int] = {}
    errors = 0
    for e in entries:
        app = (e.get("app") or "unknown").split(" - ")[-1][:40]
        apps[app] = apps.get(app, 0) + 1
        if re.search(r"(?i)error|exception|failed|traceback", e.get("summary", "")):
            errors += 1
    top = sorted(apps.items(), key=lambda kv: kv[1], reverse=True)[:8]
    return {
        "total_entries": len(entries),
        "entries_with_errors": errors,
        "top_contexts": [{"app": a, "count": c} for a, c in top],
        "first_ts": entries[0]["ts"] if entries else None,
        "last_ts": entries[-1]["ts"] if entries else None,
    }


# ----------------------------------------------------------- capture helpers
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _capture_available() -> bool:
    try:
        import mss  # noqa: F401
        import PIL  # noqa: F401

        return True
    except Exception:
        return False


def _grab_screen_png() -> Optional[bytes]:
    try:
        import io

        import mss
        from PIL import Image as PILImage

        with mss.mss() as sct:
            monitor = sct.monitors[0]  # all monitors combined
            raw = sct.grab(monitor)
            img = PILImage.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            # Downscale to keep tokens/cost and storage low.
            img.thumbnail((1280, 1280))
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue()
    except Exception:
        return None


def _vision_summary(png_bytes: bytes, settings, prompt: str) -> Optional[str]:
    """Summarize a screenshot with the user's configured (vision) model."""
    import tempfile

    from buddy.agent import Agent
    from buddy.code.agent import build_model

    settings.apply_to_env()
    model = build_model(settings)
    agent = Agent(model=model, markdown=False)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        tf.write(png_bytes)
        tmp_path = tf.name
    try:
        # Buddy exposes media via buddy.media.Image; import lazily.
        try:
            from buddy.media import Image as BuddyImage  # type: ignore

            resp = agent.run(prompt, images=[BuddyImage(filepath=tmp_path)])
        except Exception:
            from buddy.media import Image as BuddyImage  # type: ignore

            resp = agent.run(prompt, images=[BuddyImage(filepath=Path(tmp_path))])
        text = getattr(resp, "content", None) or str(resp)
        return text.strip() if text else None
    finally:
        try:
            Path(tmp_path).unlink()
        except Exception:
            pass


def _ocr_text(png_bytes: bytes) -> Optional[str]:
    try:
        import io

        import pytesseract  # type: ignore
        from PIL import Image as PILImage

        img = PILImage.open(io.BytesIO(png_bytes))
        text = pytesseract.image_to_string(img)
        return " ".join(text.split())[:400] if text else None
    except Exception:
        return None


__all__ = [
    "ScreenObserver",
    "ObserverConfig",
    "load_config",
    "save_config",
    "read_journal",
    "clear_journal",
    "insights",
]
