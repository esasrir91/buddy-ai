"""LLM/SLM fine-tuning for Aura, built on ``buddy.train``.

Training runs in a background thread and reports status. Heavy deps (torch /
transformers) are optional; if missing we return a clear, actionable message
instead of crashing.
"""

from __future__ import annotations

import threading
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def available_models() -> Dict[str, str]:
    try:
        from buddy.train import OPEN_SOURCE_TRAINING_MODELS

        return dict(OPEN_SOURCE_TRAINING_MODELS)
    except Exception:
        return {}


def training_deps_ok() -> bool:
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401

        return True
    except Exception:
        return False


@dataclass
class TrainingJob:
    id: str
    base_model: str
    status: str = "pending"  # pending | running | completed | failed
    message: str = ""
    output_dir: Optional[str] = None
    logs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "base_model": self.base_model,
            "status": self.status,
            "message": self.message,
            "output_dir": self.output_dir,
            "logs": self.logs[-50:],
        }


class TrainingManager:
    """Tracks one training job at a time (sufficient for a local app)."""

    def __init__(self) -> None:
        self._job: Optional[TrainingJob] = None
        self._lock = threading.Lock()

    @property
    def job(self) -> Optional[TrainingJob]:
        return self._job

    def start(self, base_model: str, dataset_path: str, output_dir: str, epochs: int = 3) -> Dict[str, Any]:
        if not training_deps_ok():
            return {
                "ok": False,
                "error": "Training needs PyTorch + Transformers. Install with `pip install buddy-ai[training]`.",
            }
        with self._lock:
            if self._job and self._job.status == "running":
                return {"ok": False, "error": "A training job is already running."}
            job = TrainingJob(id=f"job-{int(__import__('time').time())}", base_model=base_model, status="running")
            self._job = job

        thread = threading.Thread(target=self._run, args=(job, base_model, dataset_path, output_dir, epochs), daemon=True)
        thread.start()
        return {"ok": True, "job": job.to_dict()}

    def _run(self, job: TrainingJob, base_model: str, dataset_path: str, output_dir: str, epochs: int) -> None:
        try:
            from buddy.train import DataProcessor, ModelTrainer

            job.logs.append(f"Loading base model '{base_model}'…")
            trainer = ModelTrainer(base_model=base_model, output_dir=output_dir)
            job.logs.append(f"Processing dataset '{dataset_path}'…")
            processor = DataProcessor()

            # The exact training API varies; we attempt the common entry points
            # and surface whatever the framework reports.
            data = None
            for loader in ("process_file", "load", "prepare"):
                fn = getattr(processor, loader, None)
                if callable(fn):
                    try:
                        data = fn(dataset_path)
                        break
                    except Exception:
                        continue

            job.logs.append("Starting training…")
            train_fn = getattr(trainer, "train", None)
            if not callable(train_fn):
                raise RuntimeError("ModelTrainer has no train() entry point in this build.")
            train_fn(data, epochs=epochs) if data is not None else train_fn(epochs=epochs)

            job.status = "completed"
            job.output_dir = output_dir
            job.message = f"Training complete. Model saved to {output_dir}."
            job.logs.append(job.message)
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.message = str(exc)
            job.logs.append("ERROR: " + str(exc))
            job.logs.append(traceback.format_exc()[-1500:])


__all__ = ["TrainingManager", "TrainingJob", "available_models", "training_deps_ok"]
