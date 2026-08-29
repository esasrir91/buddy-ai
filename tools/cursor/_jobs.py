"""Background Shell job registry for AwaitShell."""
from __future__ import annotations
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Job:
    id: str
    command: str
    proc: subprocess.Popen
    output_lines: list[str] = field(default_factory=list)
    exit_code: Optional[int] = None
    started_at: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _thread: Optional[threading.Thread] = field(default=None, repr=False)

    @property
    def running(self) -> bool:
        return self.exit_code is None

    def get_output(self) -> str:
        with self._lock:
            return "".join(self.output_lines)

    def _collect(self) -> None:
        assert self.proc.stdout is not None
        for raw in iter(self.proc.stdout.readline, b""):
            line = raw.decode(errors="replace")
            with self._lock:
                self.output_lines.append(line)
        self.proc.wait()
        self.exit_code = self.proc.returncode


class JobRegistry:
    _instance: Optional["JobRegistry"] = None

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self._seq = 0

    @classmethod
    def get(cls) -> "JobRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self, command: str, cwd: Optional[str] = None) -> str:
        import platform
        if platform.system() == "Windows":
            shell_cmd = ["powershell", "-NoLogo", "-Command", command]
        else:
            shell_cmd = ["/bin/bash", "-c", command]

        proc = subprocess.Popen(
            shell_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
        )
        with self._lock:
            self._seq += 1
            job_id = f"job_{self._seq}"
            job = Job(id=job_id, command=command, proc=proc)
            t = threading.Thread(target=job._collect, daemon=True)
            job._thread = t
            self._jobs[job_id] = job
            t.start()
        return job_id

    def poll(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def wait(self, job_id: str, timeout: float = 30.0) -> Optional[Job]:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        deadline = time.time() + timeout
        while job.running and time.time() < deadline:
            time.sleep(0.2)
        return job

    def cleanup(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)
