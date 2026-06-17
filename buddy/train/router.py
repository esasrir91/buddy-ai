"""
Fire / Buddy Train — FastAPI router for the training UI.

All routes are prefixed with /api/train and mounted onto PulseApp.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from buddy.train import (
    DEFAULT_MODELS_DIR,
    delete_model,
    get_available_models,
    resolve_model_name,
)
from buddy.train.data_processor import DataProcessor
from buddy.train.jobs import DEFAULT_MODEL_NAME, LOCAL_FREE_MODELS, job_manager
from buddy.train.model_manager import ModelManager

router = APIRouter(prefix="/api/train", tags=["Fire Train"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PreviewRequest(BaseModel):
    dataset_id: str


class StartJobRequest(BaseModel):
    name: str = Field(default=DEFAULT_MODEL_NAME, description="Model name (default: fire)")
    dataset_id: str = Field(..., description="Upload batch ID from /datasets/upload")
    base_model: str = Field(default="distilgpt2", description="Base model alias or HuggingFace ID")
    description: Optional[str] = None
    epochs: int = Field(default=3, ge=1, le=50)
    batch_size: int = Field(default=4, ge=1, le=64)
    learning_rate: float = Field(default=5e-5, gt=0)
    max_length: int = Field(default=512, ge=64, le=4096)
    force: bool = False


class TestModelRequest(BaseModel):
    prompt: str = "Hello, who are you?"
    max_length: int = Field(default=150, ge=10, le=2048)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


# ---------------------------------------------------------------------------
# System & catalog
# ---------------------------------------------------------------------------


@router.get("/system")
def get_system_info() -> Dict[str, Any]:
    """Hardware and dependency info for the training UI."""
    training_available = True
    training_error: Optional[str] = None
    try:
        import torch  # noqa: F401
        from transformers import Trainer  # noqa: F401
    except ImportError as e:
        training_available = False
        training_error = str(e)

    cuda_available = False
    cuda_device = None
    if training_available:
        import torch

        cuda_available = torch.cuda.is_available()
        if cuda_available:
            cuda_device = torch.cuda.get_device_name(0)

    return {
        "training_available": training_available,
        "training_error": training_error,
        "install_hint": "Run: buddy train install-deps",
        "cuda_available": cuda_available,
        "cuda_device": cuda_device,
        "device": "cuda" if cuda_available else "cpu",
        "models_dir": DEFAULT_MODELS_DIR,
        "default_model_name": DEFAULT_MODEL_NAME,
        "local_only": True,
        "cost": "free",
    }


@router.get("/models/available")
def get_available_base_models() -> Dict[str, Any]:
    """Local-free base models recommended for offline training."""
    all_models = get_available_models()
    local = [
        {
            "id": alias,
            "hf_id": hf_id,
            "local_free": True,
            "recommended": alias in ("distilgpt2", "dialogpt-small", "phi-2"),
        }
        for alias, hf_id in LOCAL_FREE_MODELS.items()
    ]
    gated = [
        {"id": alias, "hf_id": hf_id, "local_free": False, "recommended": False}
        for alias, hf_id in all_models.items()
        if alias not in LOCAL_FREE_MODELS
    ]
    return {
        "local_free": local,
        "gated": gated,
        "default": "distilgpt2",
    }


# ---------------------------------------------------------------------------
# Trained models
# ---------------------------------------------------------------------------


@router.get("/models")
def get_trained_models() -> Dict[str, Any]:
    models = _list_models_quiet()
    return {"models": models, "count": len(models)}


def _list_models_quiet() -> List[Dict[str, Any]]:
    if not os.path.exists(DEFAULT_MODELS_DIR):
        return []
    models = []
    for model_name in os.listdir(DEFAULT_MODELS_DIR):
        model_path = os.path.join(DEFAULT_MODELS_DIR, model_name)
        metadata_path = os.path.join(model_path, "metadata.json")
        if os.path.isdir(model_path):
            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as f:
                    models.append(json.load(f))
            else:
                models.append(
                    {
                        "name": model_name,
                        "description": "Legacy model",
                        "created_at": "Unknown",
                    }
                )
    return sorted(models, key=lambda m: m.get("created_at", ""), reverse=True)


@router.delete("/models/{name}")
def remove_model(name: str) -> Dict[str, Any]:
    if not delete_model(name):
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")
    return {"deleted": True, "name": name}


@router.post("/models/{name}/test")
def test_trained_model(name: str, body: TestModelRequest) -> Dict[str, Any]:
    model_path = os.path.join(DEFAULT_MODELS_DIR, name)
    if not os.path.isdir(model_path):
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found")

    try:
        manager = ModelManager()
        load_result = json.loads(manager.load_model(model_path))
        if load_result.get("status") != "success":
            raise HTTPException(status_code=500, detail=load_result.get("message", "Failed to load model"))

        gen_result = json.loads(
            manager.generate_text(
                body.prompt,
                max_length=body.max_length,
                temperature=body.temperature,
            )
        )
        manager.unload_model()

        if gen_result.get("status") != "success":
            raise HTTPException(status_code=500, detail=gen_result.get("message", "Generation failed"))

        texts = gen_result.get("generated_texts") or [""]
        return {
            "name": name,
            "prompt": body.prompt,
            "response": texts[0],
            "generation_time": gen_result.get("generation_time"),
            "local_only": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ---------------------------------------------------------------------------
# Dataset upload & preview
# ---------------------------------------------------------------------------


@router.post("/datasets/upload")
async def upload_dataset(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    upload_id, upload_path = job_manager.create_upload_dir()
    saved: List[str] = []

    for uf in files:
        # Preserve relative paths from webkitRelativePath if present (folder upload)
        raw_name = uf.filename or "file.txt"
        # Strip any path traversal
        safe_name = raw_name.replace("\\", "/").lstrip("/")
        if ".." in safe_name.split("/"):
            safe_name = Path(safe_name).name

        dest = upload_path / safe_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = await uf.read()
        dest.write_bytes(content)
        saved.append(safe_name)

    return {
        "dataset_id": upload_id,
        "path": str(upload_path),
        "files": saved,
        "file_count": len(saved),
    }


@router.post("/datasets/preview")
def preview_dataset(body: PreviewRequest) -> Dict[str, Any]:
    from buddy.train.jobs import UPLOADS_DIR

    data_path = UPLOADS_DIR / body.dataset_id
    if not data_path.exists():
        raise HTTPException(status_code=404, detail=f"Dataset '{body.dataset_id}' not found")

    processor = DataProcessor()
    processed = processor.process_directory(str(data_path))

    samples = processed.texts[:5]
    preview_snippets = [s[:300] + ("…" if len(s) > 300 else "") for s in samples]

    return {
        "dataset_id": body.dataset_id,
        "stats": processed.stats,
        "sample_count": len(processed.texts),
        "preview": preview_snippets,
        "ready": len(processed.texts) > 0,
    }


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: str) -> Dict[str, Any]:
    from buddy.train.jobs import UPLOADS_DIR

    data_path = UPLOADS_DIR / dataset_id
    if not data_path.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")
    shutil.rmtree(data_path)
    return {"deleted": True, "dataset_id": dataset_id}


# ---------------------------------------------------------------------------
# Training jobs
# ---------------------------------------------------------------------------


@router.get("/jobs")
def list_training_jobs() -> Dict[str, Any]:
    jobs = job_manager.list_jobs()
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/jobs/{job_id}")
def get_training_job(job_id: str) -> Dict[str, Any]:
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.get("/jobs/{job_id}/events")
def get_job_events(job_id: str, since: int = 0) -> Dict[str, Any]:
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    events = job_manager.get_events(job_id, since=since)
    return {"events": events, "since": since, "total": len(job.events)}


@router.post("/jobs")
def start_training_job(body: StartJobRequest) -> Dict[str, Any]:
    from buddy.train.jobs import UPLOADS_DIR

    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Model name is required")

    data_path = UPLOADS_DIR / body.dataset_id
    if not data_path.exists():
        raise HTTPException(status_code=404, detail=f"Dataset '{body.dataset_id}' not found")

    # Restrict to local-free models unless explicitly using full HF id
    if body.base_model in LOCAL_FREE_MODELS or body.base_model in get_available_models():
        base = body.base_model
    else:
        base = resolve_model_name(body.base_model)

    try:
        job = job_manager.start_job(
            name=body.name.strip(),
            data_path=str(data_path),
            base_model=base,
            description=body.description,
            epochs=body.epochs,
            batch_size=body.batch_size,
            learning_rate=body.learning_rate,
            max_length=body.max_length,
            force=body.force,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"job": job.to_dict(), "stream_url": f"/api/train/jobs/{job.id}/stream"}


@router.post("/jobs/{job_id}/cancel")
def cancel_training_job(job_id: str) -> Dict[str, Any]:
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    cancelled = job.cancel()
    return {"cancelled": cancelled, "job": job.to_dict()}


@router.websocket("/jobs/{job_id}/stream")
async def job_progress_stream(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    job = job_manager.get_job(job_id)
    if not job:
        await websocket.send_json({"error": "Job not found", "done": True})
        await websocket.close()
        return

    cursor = 0
    try:
        while True:
            events = job_manager.get_events(job_id, since=cursor)
            for event in events:
                await websocket.send_json({"event": event, "done": False})
                cursor += 1

            status = job.status.value
            await websocket.send_json(
                {
                    "status": status,
                    "progress": job.progress,
                    "phase": job.phase,
                    "message": job.message,
                    "done": status in ("completed", "failed", "cancelled"),
                }
            )

            if status in ("completed", "failed", "cancelled"):
                break

            await asyncio.sleep(0.75)
    except WebSocketDisconnect:
        return
    except Exception as e:
        await websocket.send_json({"error": str(e), "done": True})
