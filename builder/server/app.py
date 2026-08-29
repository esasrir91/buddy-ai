"""FastAPI backend for the Buddy Builder.

Endpoints
---------
GET    /api/health              - liveness
GET    /api/catalog             - all node types, capabilities, triggers, evals
POST   /api/catalog/rebuild     - force re-introspection of the framework
GET    /api/projects            - list saved graphs
GET    /api/projects/{id}       - load a graph
PUT    /api/projects/{id}       - create/update a graph
DELETE /api/projects/{id}       - delete a graph
POST   /api/compile             - validate + compile a graph (no run)
POST   /api/run                 - compile + run, streaming events via SSE

The built frontend (if present at ``buddy/builder/server/static``) is served at ``/``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

from buddy.builder.compiler import compile_graph
from buddy.builder.compiler.errors import CompileError
from buddy.builder.registry import build_catalog
from buddy.builder.runner import run_graph
from buddy.builder.server.store import ProjectStore
from buddy.builder.spec.schema import GraphSpec

_STATIC_DIR = Path(__file__).parent / "static"


class RunRequest(BaseModel):
    spec: Dict[str, Any]
    message: str


def create_app() -> FastAPI:
    # Load local API keys if a .env is present (best-effort).
    _load_env()

    app = FastAPI(title="Buddy Builder", version="1.0", docs_url="/api/docs")
    store = ProjectStore()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ----------------------------------------------------------------- meta
    @app.get("/api/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok"}

    @app.get("/api/catalog")
    def catalog() -> JSONResponse:
        return JSONResponse(json.loads(build_catalog().model_dump_json()))

    @app.post("/api/catalog/rebuild")
    def rebuild_catalog() -> JSONResponse:
        cat = build_catalog(force=True)
        return JSONResponse({"node_types": len(cat.node_types), "skipped": len(cat.skipped)})

    # ------------------------------------------------------------- projects
    @app.get("/api/projects")
    def list_projects():
        return store.list()

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str):
        try:
            return json.loads(store.get(project_id).model_dump_json())
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Project not found")

    @app.put("/api/projects/{project_id}")
    def save_project(project_id: str, spec: Dict[str, Any] = Body(...)):
        spec["id"] = project_id
        try:
            graph = GraphSpec.model_validate(spec)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Invalid graph: {exc}")
        store.save(graph)
        return {"ok": True, "id": project_id}

    @app.delete("/api/projects/{project_id}")
    def delete_project(project_id: str):
        store.delete(project_id)
        return {"ok": True}

    # -------------------------------------------------------- compile / run
    @app.post("/api/compile")
    def compile_endpoint(spec: Dict[str, Any] = Body(...)):
        try:
            graph = GraphSpec.model_validate(spec)
            compiled = compile_graph(graph)
            return {"ok": True, "kind": compiled.kind, "root": type(compiled.root).__name__}
        except CompileError as exc:
            return JSONResponse(status_code=400, content={"ok": False, "error": str(exc), "node_id": exc.node_id})
        except Exception as exc:
            return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})

    @app.post("/api/run")
    def run_endpoint(req: RunRequest):
        def event_stream():
            for event in run_graph(req.spec, req.message):
                yield f"data: {json.dumps(event.to_dict())}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # ------------------------------------------------------------- frontend
    if _STATIC_DIR.exists():
        app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(_STATIC_DIR / "index.html")

        @app.get("/{full_path:path}")
        def spa(full_path: str):
            target = _STATIC_DIR / full_path
            if target.exists() and target.is_file():
                return FileResponse(target)
            return FileResponse(_STATIC_DIR / "index.html")

    return app


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    for candidate in (
        os.getenv("BUDDY_BUILDER_ENV"),
        Path.cwd() / ".env",
        Path.cwd() / "sri" / "workspace" / "secrets" / ".env",
    ):
        if candidate and Path(candidate).exists():
            load_dotenv(candidate, override=False)


def serve(host: str = "127.0.0.1", port: int = 8500, reload: bool = False) -> None:
    import uvicorn

    if reload:
        uvicorn.run("buddy.builder.server.app:create_app", host=host, port=port, reload=True, factory=True)
    else:
        uvicorn.run(create_app(), host=host, port=port)


app = None  # lazy; use create_app()

__all__ = ["create_app", "serve"]
