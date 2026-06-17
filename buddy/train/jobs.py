"""
Training job manager for the Fire / Buddy Train UI.

Runs training in background threads and collects progress events for
REST polling and WebSocket streaming.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from buddy.train import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_LEARNING_RATE,
    DEFAULT_MAX_LENGTH,
    DEFAULT_MODELS_DIR,
    resolve_model_name,
)
from buddy.train.data_processor import DataProcessor
from buddy.train.trainer import ModelTrainer
from buddy.utils.log import logger

if TYPE_CHECKING:
    from buddy.eval.competency import CompetencyResult

UPLOADS_DIR = Path(os.path.expanduser("~")) / ".buddy" / "train" / "uploads"
DEFAULT_MODEL_NAME = "fire"

# Models that run locally without HuggingFace gating or paid APIs
LOCAL_FREE_MODELS: Dict[str, str] = {
    "distilgpt2": "distilgpt2",
    "dialogpt-small": "microsoft/DialoGPT-small",
    "dialogpt-medium": "microsoft/DialoGPT-medium",
    "phi-1_5": "microsoft/phi-1_5",
    "phi-2": "microsoft/phi-2",
    "gpt-neo-125m": "EleutherAI/gpt-neo-125M",
    "gpt-neo-1.3b": "EleutherAI/gpt-neo-1.3B",
    "bloom-560m": "bigscience/bloom-560m",
}


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING_DATA = "processing_data"
    LOADING_MODEL = "loading_model"
    TRAINING = "training"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TrainingJob:
    id: str
    name: str
    base_model: str
    data_path: str
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    phase: str = "queued"
    message: str = "Waiting to start…"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    config: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    _cancel: bool = field(default=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "base_model": self.base_model,
            "data_path": self.data_path,
            "status": self.status.value,
            "progress": round(self.progress, 4),
            "phase": self.phase,
            "message": self.message,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "result": self.result,
            "config": self.config,
            "event_count": len(self.events),
        }

    def emit(self, phase: str, message: str, progress: float, **extra: Any) -> None:
        with self._lock:
            self.phase = phase
            self.message = message
            self.progress = max(0.0, min(1.0, progress))
            event = {
                "ts": datetime.now().isoformat(),
                "phase": phase,
                "message": message,
                "progress": self.progress,
                **extra,
            }
            self.events.append(event)
            if len(self.events) > 500:
                self.events = self.events[-500:]

    def cancel(self) -> bool:
        with self._lock:
            if self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                return False
            self._cancel = True
            self.status = JobStatus.CANCELLED
            self.message = "Cancelled by user"
            self.completed_at = datetime.now().isoformat()
            return True

    @property
    def is_cancelled(self) -> bool:
        with self._lock:
            return self._cancel


class TrainingJobManager:
    """Singleton-style manager for in-process training jobs."""

    def __init__(self) -> None:
        self._jobs: Dict[str, TrainingJob] = {}
        self._lock = threading.Lock()

    def list_jobs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [j.to_dict() for j in sorted(self._jobs.values(), key=lambda x: x.created_at, reverse=True)]

    def get_job(self, job_id: str) -> Optional[TrainingJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def get_events(self, job_id: str, since: int = 0) -> List[Dict[str, Any]]:
        job = self.get_job(job_id)
        if not job:
            return []
        with job._lock:
            return job.events[since:]

    def create_upload_dir(self) -> tuple[str, Path]:
        upload_id = str(uuid.uuid4())[:8]
        path = UPLOADS_DIR / upload_id
        path.mkdir(parents=True, exist_ok=True)
        return upload_id, path

    def start_job(
        self,
        *,
        name: str,
        data_path: str,
        base_model: str = "distilgpt2",
        description: Optional[str] = None,
        epochs: int = 3,
        batch_size: int = DEFAULT_BATCH_SIZE,
        learning_rate: float = DEFAULT_LEARNING_RATE,
        max_length: int = DEFAULT_MAX_LENGTH,
        force: bool = False,
    ) -> TrainingJob:
        job_id = str(uuid.uuid4())
        resolved_model = resolve_model_name(base_model)
        output_dir = os.path.join(DEFAULT_MODELS_DIR, name)

        if os.path.exists(output_dir) and not force:
            raise ValueError(f"Model '{name}' already exists. Enable force to overwrite.")

        active = self._active_job_for_name(name)
        if active:
            raise ValueError(f"A training job is already running for '{name}'.")

        job = TrainingJob(
            id=job_id,
            name=name,
            base_model=resolved_model,
            data_path=data_path,
            config={
                "description": description or f"Fire model trained on uploaded data",
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "max_length": max_length,
                "force": force,
            },
        )

        with self._lock:
            self._jobs[job_id] = job

        thread = threading.Thread(target=self._run_job, args=(job,), daemon=True)
        thread.start()
        return job

    def enqueue_from_competency(
        self,
        result: "CompetencyResult",
        data_paths: Dict[str, str],
        *,
        deficit_threshold: float = 0.0,
        max_jobs: Optional[int] = None,
        base_model: str = "distilgpt2",
        name_prefix: str = "competency",
        **job_kwargs: Any,
    ) -> List[TrainingJob]:
        """Close the competency loop: start retraining jobs for the weakest domains.

        Given a :class:`~buddy.eval.competency.CompetencyResult` and a mapping of
        ``domain -> training data path``, this ranks domains by deficit-driven
        priority and starts a fine-tuning job for each domain whose deficit
        exceeds ``deficit_threshold`` (highest priority first). Domains without a
        corresponding entry in ``data_paths`` are skipped.
        """
        from buddy.eval.competency import DeficitDrivenController

        controller = DeficitDrivenController(
            deficit_threshold=deficit_threshold,
            max_actions=max_jobs,
        )
        started: List[TrainingJob] = []
        for action in controller.recommend(result):
            data_path = data_paths.get(action.domain)
            if not data_path:
                logger.debug(f"No training data for domain '{action.domain}'; skipping.")
                continue
            try:
                job = self.start_job(
                    name=f"{name_prefix}-{action.domain}",
                    data_path=data_path,
                    base_model=base_model,
                    description=action.reason,
                    **job_kwargs,
                )
            except ValueError as e:
                # e.g. a job for this domain is already running, or the model
                # exists and force is disabled. In autonomous operation we skip
                # rather than fail the whole cycle.
                logger.debug(f"Skipping training for domain '{action.domain}': {e}")
                continue
            started.append(job)
            if max_jobs is not None and len(started) >= max_jobs:
                break
        return started

    def _active_job_for_name(self, name: str) -> Optional[TrainingJob]:
        with self._lock:
            for job in self._jobs.values():
                if job.name == name and job.status not in (
                    JobStatus.COMPLETED,
                    JobStatus.FAILED,
                    JobStatus.CANCELLED,
                ):
                    return job
        return None

    def _run_job(self, job: TrainingJob) -> None:
        job.started_at = datetime.now().isoformat()
        job.status = JobStatus.PROCESSING_DATA
        job.emit("processing_data", "Reading and processing training files…", 0.05)

        try:
            if job.is_cancelled:
                return

            if not os.path.exists(job.data_path):
                raise FileNotFoundError(f"Data path not found: {job.data_path}")

            processor = DataProcessor()
            processed_data = processor.process_directory(job.data_path)

            if not processed_data.texts:
                raise ValueError("No valid training data found in uploaded files")

            stats = processed_data.stats
            job.emit(
                "processing_data",
                f"Processed {stats.get('processed_files', 0)} files ({stats.get('total_characters', 0):,} chars)",
                0.15,
                stats=stats,
            )

            if job.is_cancelled:
                return

            job.status = JobStatus.LOADING_MODEL
            job.emit("loading_model", f"Loading base model {job.base_model}…", 0.2)

            output_dir = Path(DEFAULT_MODELS_DIR) / job.name
            if output_dir.exists() and job.config.get("force"):
                shutil.rmtree(output_dir)

            output_dir.mkdir(parents=True, exist_ok=True)

            trainer = ModelTrainer(base_model=job.base_model, output_dir=output_dir)

            def on_progress(payload: Dict[str, Any]) -> None:
                if job.is_cancelled:
                    return
                logs = payload.get("logs") or {}
                loss = logs.get("loss") or logs.get("train_loss")
                step_msg = payload.get("step", "training")
                progress = payload.get("progress", job.progress)
                job.status = JobStatus.TRAINING
                job.emit(
                    "training",
                    f"Training — {step_msg}" + (f" (loss: {loss:.4f})" if isinstance(loss, float) else ""),
                    progress,
                    logs=logs if logs else None,
                )

            training_config = {
                "num_epochs": job.config["epochs"],
                "batch_size": job.config["batch_size"],
                "learning_rate": job.config["learning_rate"],
                "max_length": job.config["max_length"],
                "progress_callback": on_progress,
            }

            if job.is_cancelled:
                return

            job.status = JobStatus.TRAINING
            job.emit("training", "Starting fine-tuning…", 0.25)

            results = trainer.train_from_data(processed_data, training_config)

            if job.is_cancelled:
                return

            job.status = JobStatus.SAVING
            job.emit("saving", "Saving model metadata…", 0.95)

            total_chars = sum(len(t) for t in processed_data.texts)
            metadata = {
                "name": job.name,
                "description": job.config.get("description"),
                "base_model": job.base_model,
                "epochs": job.config["epochs"],
                "data_path": job.data_path,
                "num_files": stats.get("processed_files", 0),
                "total_characters": total_chars,
                "created_at": datetime.now().isoformat(),
                "local_only": True,
                "provider": "fire",
            }

            with open(output_dir / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)

            job.status = JobStatus.COMPLETED
            job.progress = 1.0
            job.completed_at = datetime.now().isoformat()
            job.result = results
            job.emit("completed", f"Model '{job.name}' is ready!", 1.0, result=results)
            logger.info(f"Training job {job.id} completed: {job.name}")

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now().isoformat()
            job.emit("failed", f"Training failed: {e}", job.progress, error=str(e))
            logger.error(f"Training job {job.id} failed: {e}")


job_manager = TrainingJobManager()
