"""
PulseApp — a FastAPI application that serves the PULSE backend API and React UI.

One command starts everything:
    from buddy.pulse.app import PulseApp
    PulseApp().serve()

Or via CLI:
    buddy pulse start
"""
from __future__ import annotations

import os
import webbrowser
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from buddy.pulse.router import router


class PulseApp:
    """
    Hosts the PULSE FastAPI backend and serves the built React frontend.

    The React build is expected at:
        <package_root>/pulse-ui/dist/

    If the build does not exist, the app still runs — the /api/pulse/* routes
    are available, and the root serves a simple redirect page.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8888,
        open_browser: bool = True,
        title: str = "PULSE — Virtual Employee",
        description: str = "The heartbeat of your team.",
    ) -> None:
        self.host = host
        self.port = port
        self.open_browser = open_browser

        self.app = FastAPI(
            title=title,
            description=description,
            version="2.1.0",
            docs_url="/api/docs",
            redoc_url="/api/redoc",
        )

        # CORS — allow the React dev server (localhost:5173) during development
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Mount PULSE API router
        self.app.include_router(router)

        # Mount React static build if it exists
        self._mount_ui()

    def _mount_ui(self) -> None:
        """Mount the compiled React frontend at / if the build exists."""
        # Look for the built UI relative to this file
        here = Path(__file__).parent
        # Could be: <project_root>/pulse-ui/dist
        candidates = [
            here.parent.parent / "pulse-ui" / "dist",
            here.parent / "pulse-ui" / "dist",
            Path(os.getcwd()) / "pulse-ui" / "dist",
        ]
        ui_dist: Optional[Path] = None
        for candidate in candidates:
            if candidate.exists() and (candidate / "index.html").exists():
                ui_dist = candidate
                break

        if ui_dist:
            self.app.mount("/assets", StaticFiles(directory=str(ui_dist / "assets")), name="assets")

            @self.app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
            async def serve_spa(full_path: str) -> HTMLResponse:
                # Don't intercept API routes
                if full_path.startswith("api/"):
                    from fastapi import HTTPException
                    raise HTTPException(status_code=404)
                index = ui_dist / "index.html"  # type: ignore[operator]
                return HTMLResponse(content=index.read_text(encoding="utf-8"))
        else:
            @self.app.get("/", response_class=HTMLResponse, include_in_schema=False)
            async def serve_placeholder() -> HTMLResponse:
                return HTMLResponse(content=_placeholder_html(self.port))

    def serve(self) -> None:
        """Start the PULSE server (blocking)."""
        url = f"http://{self.host}:{self.port}"
        print(f"\n🔵 PULSE is running at {url}")
        print(f"   API docs → {url}/api/docs\n")

        if self.open_browser:
            import threading
            threading.Timer(1.5, lambda: webbrowser.open(url)).start()

        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")


def _placeholder_html(port: int) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>PULSE — Virtual Employee</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #0f172a;
      color: #f1f5f9;
      font-family: system-ui, -apple-system, sans-serif;
      display: flex; align-items: center; justify-content: center;
      min-height: 100vh;
    }}
    .card {{
      text-align: center;
      max-width: 520px;
      padding: 48px 40px;
      background: #1e293b;
      border-radius: 20px;
      border: 1px solid #334155;
      box-shadow: 0 25px 50px rgba(0,0,0,0.5);
    }}
    .pulse-dot {{
      width: 20px; height: 20px;
      background: #3b82f6;
      border-radius: 50%;
      margin: 0 auto 24px;
      animation: pulse 1.5s ease-in-out infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ box-shadow: 0 0 0 0 rgba(59,130,246,0.6); }}
      50% {{ box-shadow: 0 0 0 16px rgba(59,130,246,0); }}
    }}
    h1 {{ font-size: 2rem; font-weight: 700; margin-bottom: 8px; }}
    .subtitle {{ color: #94a3b8; margin-bottom: 32px; font-size: 1.05rem; }}
    .badge {{
      display: inline-block;
      background: #1d4ed8;
      color: #bfdbfe;
      padding: 4px 12px;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 600;
      margin-bottom: 32px;
    }}
    .links {{ display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }}
    a {{
      display: inline-block;
      padding: 10px 24px;
      background: #3b82f6;
      color: white;
      text-decoration: none;
      border-radius: 8px;
      font-weight: 500;
      transition: background 0.2s;
    }}
    a:hover {{ background: #2563eb; }}
    a.secondary {{
      background: #1e293b;
      border: 1px solid #475569;
      color: #94a3b8;
    }}
    a.secondary:hover {{ background: #334155; color: #f1f5f9; }}
    .note {{
      margin-top: 28px;
      font-size: 0.85rem;
      color: #64748b;
      line-height: 1.6;
    }}
    code {{
      background: #0f172a;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: monospace;
      color: #7dd3fc;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="pulse-dot"></div>
    <div class="badge">PULSE is running</div>
    <h1>Virtual Employee's ERA</h1>
    <p class="subtitle">The heartbeat of your team — powered by Buddy AI</p>
    <div class="links">
      <a href="/api/docs">API Docs</a>
      <a href="/api/redoc" class="secondary">ReDoc</a>
    </div>
    <p class="note">
      The React UI hasn't been built yet.<br/>
      Run <code>cd pulse-ui && npm install && npm run build</code><br/>
      then restart PULSE to see the full interface.
    </p>
  </div>
</body>
</html>"""
