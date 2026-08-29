"""BashTool – stateful bash / shell client tool.

Mirrors the Anthropic ``bash_20250124`` client tool with a persistent
subprocess session so that environment changes (``cd``, ``export``, etc.)
are carried across commands within the same agent run.

Works with **any LLM** – the tool is always executed locally by the agent
framework regardless of the underlying model.

Usage::

    from buddy.tools.bash_tool import BashTool

    agent = Agent(model=..., tools=[BashTool()])
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, List, Optional

from buddy.tools.toolkit import Toolkit

logger = logging.getLogger(__name__)

# Type string emitted when building an Anthropic-style tool list
ANTHROPIC_TOOL_TYPE = "bash_20250124"


class BashSession:
    """A persistent shell session backed by a long-running subprocess."""

    _SENTINEL = "<<<__BUDDY_BASH_DONE__>>>"

    def __init__(self, timeout: int = 120, working_directory: Optional[str] = None):
        self.timeout = timeout
        self.working_directory = working_directory or os.getcwd()
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self._start()

    def _start(self) -> None:
        shell = "bash" if sys.platform != "win32" else "cmd"
        self._proc = subprocess.Popen(
            [shell],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=self.working_directory,
            env=os.environ.copy(),
        )

    def run(self, command: str) -> str:
        """Execute a command in the persistent shell and return combined output."""
        if self._proc is None or self._proc.poll() is not None:
            self._start()

        sentinel_cmd = f'echo "{self._SENTINEL}"'
        full_cmd = f"{command}\n{sentinel_cmd}\n"

        with self._lock:
            assert self._proc and self._proc.stdin and self._proc.stdout
            try:
                self._proc.stdin.write(full_cmd)
                self._proc.stdin.flush()
            except BrokenPipeError:
                self._start()
                self._proc.stdin.write(full_cmd)  # type: ignore[union-attr]
                self._proc.stdin.flush()  # type: ignore[union-attr]

            lines: List[str] = []
            import select
            import time

            deadline = time.monotonic() + self.timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return "\n".join(lines) + f"\n[Timed out after {self.timeout}s]"
                ready, _, _ = select.select([self._proc.stdout], [], [], min(remaining, 0.5))
                if ready:
                    line = self._proc.stdout.readline()
                    if self._SENTINEL in line:
                        break
                    lines.append(line.rstrip("\n"))
                elif self._proc.poll() is not None:
                    break

            return "\n".join(lines)

    def close(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()
        self._proc = None


class _SimpleBashSession:
    """Fallback: run each command in a fresh subprocess (Windows-safe)."""

    def __init__(self, timeout: int = 120, working_directory: Optional[str] = None):
        self.timeout = timeout
        self.working_directory = working_directory or os.getcwd()

    def run(self, command: str) -> str:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.working_directory,
            )
            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr
            return output.rstrip()
        except subprocess.TimeoutExpired:
            return f"[Timed out after {self.timeout}s]"
        except Exception as exc:
            return f"Error: {exc}"

    def close(self) -> None:
        pass


def _make_session(timeout: int, working_directory: Optional[str], stateful: bool):
    if stateful and sys.platform != "win32":
        try:
            import select  # noqa: F401
            return BashSession(timeout=timeout, working_directory=working_directory)
        except Exception:
            pass
    return _SimpleBashSession(timeout=timeout, working_directory=working_directory)


class BashTool(Toolkit):
    """Run shell commands in a persistent bash session.

    Equivalent to Anthropic's ``bash_20250124`` client tool, but works with
    any LLM.  The shell state persists between calls within the same
    ``BashTool`` instance (working directory, environment variables, etc.).

    Parameters
    ----------
    working_directory:
        Starting directory for the session.  Defaults to the current directory.
    timeout:
        Maximum seconds to wait for a single command.
    stateful:
        If ``True`` (default on Linux/macOS), maintain a persistent shell
        process across commands.  If ``False``, each command runs in its own
        fresh subprocess.
    restart_on_error:
        Restart the shell session if a command exits with a non-zero code.
    allowed_commands:
        Optional allowlist of command prefixes.  Any command not starting with
        one of these strings is rejected.
    blocked_commands:
        Denylist of command prefixes (e.g. ``["rm -rf /", "sudo"]``).
    """

    ANTHROPIC_TOOL_TYPE = ANTHROPIC_TOOL_TYPE

    def __init__(
        self,
        working_directory: Optional[str] = None,
        timeout: int = 120,
        stateful: bool = True,
        restart_on_error: bool = False,
        allowed_commands: Optional[List[str]] = None,
        blocked_commands: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        self._working_directory = working_directory
        self._timeout = timeout
        self._stateful = stateful
        self._restart_on_error = restart_on_error
        self._allowed_commands = allowed_commands
        self._blocked_commands = blocked_commands or [
            "rm -rf /",
            "rm -rf ~",
            ":(){:|:&};:",  # fork bomb
        ]
        self._session = _make_session(timeout, working_directory, stateful)

        super().__init__(
            name="bash",
            tools=[self.bash],
            instructions=(
                "Use the bash tool to run shell commands. "
                "The shell session persists between calls, so environment variables "
                "and the working directory are maintained. "
                "Always handle errors by checking output for error messages."
            ),
            **kwargs,
        )

    # ── tool method ──────────────────────────────────────────────────────────

    def bash(self, command: str, restart: bool = False) -> str:
        """Execute a shell command and return its output.

        Runs the command in a persistent bash session. The working directory,
        environment variables, and other shell state are preserved between
        calls. Use this for file operations, running scripts, installing
        packages, building projects, and running tests.

        Args:
            command: The shell command to execute.
            restart: If True, restart the shell session before running the command.
                     Use this to reset the environment after a crash or timeout.

        Returns:
            str: The command output (stdout + stderr combined).
        """
        if restart:
            self._session.close()
            self._session = _make_session(self._timeout, self._working_directory, self._stateful)
            return "Shell session restarted."

        blocked = self._check_blocked(command)
        if blocked:
            return json.dumps({"error": f"Command blocked: {blocked}"})

        try:
            output = self._session.run(command)
            return output if output else "(no output)"
        except Exception as exc:
            logger.exception("Bash command failed: %s", command)
            if self._restart_on_error:
                self._session.close()
                self._session = _make_session(self._timeout, self._working_directory, self._stateful)
            return f"Error: {exc}"

    def _check_blocked(self, command: str) -> Optional[str]:
        cmd_stripped = command.strip()
        for blocked in self._blocked_commands:
            if cmd_stripped.startswith(blocked) or blocked in cmd_stripped:
                return blocked
        if self._allowed_commands:
            if not any(cmd_stripped.startswith(allowed) for allowed in self._allowed_commands):
                return f"not in allowlist ({self._allowed_commands[:3]}…)"
        return None

    def __del__(self) -> None:
        try:
            self._session.close()
        except Exception:
            pass

    def to_anthropic_client_tool(self) -> dict:
        """Return the Anthropic API client-tool declaration."""
        return {"type": self.ANTHROPIC_TOOL_TYPE}
