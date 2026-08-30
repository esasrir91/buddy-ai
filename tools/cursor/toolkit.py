"""
CursorTools – full Cursor-parity toolkit registered on a Buddy Agent.

Tool names use PascalCase to match the Cursor IDE surface.
File operations are sandboxed to the workspace root via Sandbox.
In ``plan`` mode, mutating tools refuse with a clear error.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from buddy.tools.toolkit import Toolkit
from buddy.tools.cursor._sandbox import Sandbox
from buddy.tools.cursor._jobs import JobRegistry

# Ignored directories for Glob / Grep
_IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", "dist", "build", ".next",
    ".turbo", ".idea", ".vscode", "target", ".aura", ".cursor",
}

_MAX_READ = 400_000
_MAX_GREP_RESULTS = 200


class CursorTools(Toolkit):
    """Cursor-class coding tools for the Aura IDE agent."""

    def __init__(
        self,
        base_path: str,
        enable_shell: bool = True,
        enable_browser: bool = False,
        mode: str = "agent",          # "agent" | "plan" | "ask"
        session_id: Optional[str] = None,
        event_queue: Any = None,       # queue.Queue pushed to by _emit()
        **kwargs,
    ) -> None:
        self._sb = Sandbox(base_path)
        self._enable_shell = enable_shell
        self._enable_browser = enable_browser
        self._mode = mode
        self._session_id = session_id
        self._event_queue = event_queue   # set by the chat endpoint before running

        # Start with no tools list; we register manually below
        super().__init__(name="cursor_tools", tools=[], auto_register=False, **kwargs)
        self._register_all()

    # ── helpers ────────────────────────────────────────────────────────────

    def _mutating_check(self) -> None:
        """Raise in plan/ask mode to prevent unintended mutations."""
        if self._mode == "plan":
            raise RuntimeError(
                "Mutating tools are disabled in Plan mode. "
                "Confirm the plan first, then the agent will execute it."
            )

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Push a custom UI event to the SSE stream for this session."""
        if self._event_queue is not None:
            try:
                self._event_queue.put({"type": event_type, **data})
            except Exception:
                pass

    def _register_all(self) -> None:
        def reg(fn: Callable, name: str) -> None:
            self.register(fn, name=name)

        # Coding tools
        reg(self.read,       "Read")
        reg(self.write,      "Write")
        reg(self.str_replace, "StrReplace")
        reg(self.delete,     "Delete")
        reg(self.glob,       "Glob")
        reg(self.grep,       "Grep")

        if self._enable_shell:
            reg(self.shell,      "Shell")
            reg(self.await_shell, "AwaitShell")

        # Meta tools
        reg(self.todo_write,   "TodoWrite")
        reg(self.edit_notebook, "EditNotebook")
        reg(self.read_lints,   "ReadLints")

        # Modes
        reg(self.switch_mode,  "SwitchMode")
        reg(self.create_plan,  "CreatePlan")
        reg(self.ask_question, "AskQuestion")

        # Task subagents
        reg(self.task, "Task")

        # MCP dynamic tools
        reg(self.get_dynamic_tools, "GetDynamicTools")
        reg(self.call_dynamic_tool, "CallDynamicTool")
        reg(self.fetch_mcp_resource, "FetchMcpResource")

        # Browser tools (Playwright)
        if self._enable_browser:
            reg(self.browser_navigate,      "browser_navigate")
            reg(self.browser_snapshot,      "browser_snapshot")
            reg(self.browser_click,         "browser_click")
            reg(self.browser_type,          "browser_type")
            reg(self.browser_fill,          "browser_fill")
            reg(self.browser_press_key,     "browser_press_key")
            reg(self.browser_scroll,        "browser_scroll")
            reg(self.browser_take_screenshot, "browser_take_screenshot")
            reg(self.browser_tabs,          "browser_tabs")

    # ══════════════════════════════════════════════════════════════════════
    # CODING TOOLS
    # ══════════════════════════════════════════════════════════════════════

    def read(
        self,
        path: str,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> str:
        """Read the contents of a file.

        Args:
            path (str): Workspace-relative (or absolute) path to the file.
            offset (int): 1-based line number to start reading from.
            limit (int): Maximum number of lines to return.

        Returns:
            str: File contents, with 1-based line numbers prefixed.
        """
        p = self._sb.resolve(path)
        if not p.exists():
            return f"Error: file not found: {path}"
        if not p.is_file():
            return f"Error: {path} is a directory"
        try:
            raw = p.read_bytes()[:_MAX_READ]
            text = raw.decode(errors="replace")
        except Exception as e:
            return f"Error reading {path}: {e}"

        lines = text.splitlines(keepends=True)
        start = max(0, (offset or 1) - 1)
        end = start + (limit or len(lines))
        chunk = lines[start:end]
        numbered = "".join(f"{start + i + 1:6}|{line}" for i, line in enumerate(chunk))
        extra = ""
        if len(raw) >= _MAX_READ:
            extra = f"\n… [truncated at {_MAX_READ} bytes]"
        return numbered + extra

    def write(self, path: str, content: str) -> str:
        """Create or overwrite a file with *content*.

        Args:
            path (str): Workspace-relative path of the file to write.
            content (str): Full file content.

        Returns:
            str: Confirmation message.
        """
        self._mutating_check()
        p = self._sb.resolve(path)
        old_content = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        self._emit("file_edit", {
            "path": self._sb.rel(p),
            "old_content": old_content,
            "new_content": content,
        })
        return f"Wrote {len(content)} chars to {self._sb.rel(p)}"

    def str_replace(
        self,
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> str:
        """Replace a unique string in a file.

        Args:
            path (str): Workspace-relative file path.
            old_string (str): The exact string to find (must be unique unless replace_all=True).
            new_string (str): The replacement text.
            replace_all (bool): Replace every occurrence instead of asserting uniqueness.

        Returns:
            str: Confirmation with number of replacements made.
        """
        self._mutating_check()
        p = self._sb.resolve(path)
        if not p.exists():
            return f"Error: {path} not found"
        text = p.read_text(encoding="utf-8")
        count = text.count(old_string)
        if count == 0:
            return f"Error: old_string not found in {path}"
        if not replace_all and count > 1:
            return (
                f"Error: old_string appears {count} times in {path}. "
                "Pass replace_all=True or provide more surrounding context."
            )
        new_text = text.replace(old_string, new_string, -1 if replace_all else 1)
        p.write_text(new_text, encoding="utf-8")
        self._emit("file_edit", {
            "path": self._sb.rel(p),
            "old_content": text,
            "new_content": new_text,
        })
        return f"Replaced {count if replace_all else 1} occurrence(s) in {self._sb.rel(p)}"

    def delete(self, path: str) -> str:
        """Delete a file or empty directory.

        Args:
            path (str): Workspace-relative path to delete.

        Returns:
            str: Confirmation message.
        """
        self._mutating_check()
        p = self._sb.resolve(path)
        if not p.exists():
            return f"Error: {path} does not exist"
        try:
            if p.is_file():
                p.unlink()
                return f"Deleted file: {self._sb.rel(p)}"
            else:
                import shutil
                shutil.rmtree(str(p))
                return f"Deleted directory: {self._sb.rel(p)}"
        except Exception as e:
            return f"Error deleting {path}: {e}"

    def glob(
        self,
        glob_pattern: str,
        target_directory: Optional[str] = None,
    ) -> str:
        """Find files matching a glob pattern.

        Args:
            glob_pattern (str): Glob pattern (e.g. ``**/*.py``). Patterns not
                starting with ``**/`` are automatically prepended with it.
            target_directory (str): Sub-directory to search. Defaults to workspace root.

        Returns:
            str: Newline-separated list of matching paths, sorted by modification time.
        """
        base = self._sb.resolve(target_directory or ".")
        if not glob_pattern.startswith("**/"):
            pattern = "**/" + glob_pattern
        else:
            pattern = glob_pattern
        try:
            matches = sorted(
                (p for p in base.glob(pattern)
                 if p.is_file()
                 and not any(part in _IGNORE_DIRS for part in p.parts)),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if not matches:
                return "No files matched."
            return "\n".join(self._sb.rel(m) for m in matches[:500])
        except Exception as e:
            return f"Glob error: {e}"

    def grep(
        self,
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        output_mode: str = "content",
        multiline: bool = False,
        case_insensitive: bool = False,
        head_limit: Optional[int] = None,
    ) -> str:
        """Search file contents using ripgrep (rg) with Python fallback.

        Args:
            pattern (str): Regular expression to search for.
            path (str): Directory or file to search. Defaults to workspace root.
            glob (str): File glob filter (e.g. ``*.py``).
            output_mode (str): ``"content"`` | ``"files_with_matches"`` | ``"count"``.
            multiline (bool): Enable multiline mode.
            case_insensitive (bool): Case-insensitive search.
            head_limit (int): Maximum number of results to return.

        Returns:
            str: Matching lines / file list / counts.
        """
        search_path = str(self._sb.resolve(path or "."))
        limit = head_limit or _MAX_GREP_RESULTS

        # Try rg first
        try:
            cmd = ["rg", "--no-heading", "-n"]
            if output_mode == "files_with_matches":
                cmd.append("-l")
            elif output_mode == "count":
                cmd.append("-c")
            if multiline:
                cmd += ["-U", "--multiline-dotall"]
            if case_insensitive:
                cmd.append("-i")
            if glob:
                cmd += ["--glob", glob]
            for d in _IGNORE_DIRS:
                cmd += ["--glob", f"!{d}"]
            cmd += ["--", pattern, search_path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20,
            )
            lines = result.stdout.splitlines()[:limit]
            if not lines:
                return "(no matches)"
            return "\n".join(lines)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Python fallback
        import re
        flags = re.MULTILINE
        if case_insensitive:
            flags |= re.IGNORECASE
        if multiline:
            flags |= re.DOTALL
        try:
            rx = re.compile(pattern, flags)
        except re.error as e:
            return f"Invalid regex: {e}"

        results: list[str] = []
        root = self._sb.resolve(path or ".")
        candidates = root.rglob("*") if root.is_dir() else [root]
        for fp in candidates:
            if not fp.is_file():
                continue
            if any(part in _IGNORE_DIRS for part in fp.parts):
                continue
            if glob:
                import fnmatch
                if not fnmatch.fnmatch(fp.name, glob):
                    continue
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            rel = self._sb.rel(fp)
            if output_mode == "files_with_matches":
                if rx.search(text):
                    results.append(rel)
                    if len(results) >= limit:
                        break
            elif output_mode == "count":
                n = len(rx.findall(text))
                if n:
                    results.append(f"{rel}: {n}")
                    if len(results) >= limit:
                        break
            else:
                for lno, line in enumerate(text.splitlines(), 1):
                    if rx.search(line):
                        results.append(f"{rel}:{lno}: {line}")
                        if len(results) >= limit:
                            break
                if len(results) >= limit:
                    break

        return "\n".join(results) if results else "(no matches)"

    # ══════════════════════════════════════════════════════════════════════
    # SHELL TOOLS
    # ══════════════════════════════════════════════════════════════════════

    def shell(
        self,
        command: str,
        working_directory: Optional[str] = None,
        timeout: int = 120,
        background: bool = False,
    ) -> str:
        """Run a shell command (PowerShell on Windows, bash on Unix).

        Args:
            command (str): The command to execute.
            working_directory (str): Working directory for the command.
            timeout (int): Seconds to wait before killing the process.
            background (bool): Run in the background and return a job ID.

        Returns:
            str: Command output or job_id if background=True.
        """
        self._sb.assert_enabled(self._enable_shell, "Shell")
        cwd = str(self._sb.resolve(working_directory or "."))

        if background:
            job_id = JobRegistry.get().start(command, cwd=cwd)
            return f"Started background job {job_id}. Use AwaitShell(shell_id='{job_id}') to check status."

        is_win = platform.system() == "Windows"
        shell_cmd = (
            ["powershell", "-NoLogo", "-NonInteractive", "-Command", command]
            if is_win else
            ["/bin/bash", "-c", command]
        )

        self._emit("shell_start", {"command": command, "cwd": cwd})

        try:
            import subprocess as _sp
            proc = _sp.Popen(
                shell_cmd,
                stdout=_sp.PIPE,
                stderr=_sp.STDOUT,
                text=True,
                cwd=cwd,
            )
            chunks: list[str] = []
            deadline = time.time() + timeout
            # Stream output line-by-line
            assert proc.stdout is not None
            for line in proc.stdout:
                if time.time() > deadline:
                    proc.kill()
                    self._emit("shell_end", {"command": command, "exit_code": -1, "timed_out": True})
                    combined = "".join(chunks)
                    return f"exit_code=-1 (timeout)\n{combined[-8000:]}"
                chunks.append(line)
                self._emit("shell_output", {"chunk": line})
            proc.wait()
            combined = "".join(chunks)
            self._emit("shell_end", {"command": command, "exit_code": proc.returncode})
            header = f"exit_code={proc.returncode}\n"
            return header + (combined[-8000:] if len(combined) > 8000 else combined)
        except Exception as e:
            self._emit("shell_end", {"command": command, "exit_code": -1, "error": str(e)})
            return f"Error: {e}"

    def await_shell(
        self,
        shell_id: Optional[str] = None,
        block_until_ms: int = 30000,
        pattern: Optional[str] = None,
    ) -> str:
        """Wait for or poll a background shell job.

        Args:
            shell_id (str): Job ID returned by Shell(background=True). Omit to sleep.
            block_until_ms (int): Milliseconds to wait.
            pattern (str): Return early when output matches this regex.

        Returns:
            str: Current output and status of the job.
        """
        self._sb.assert_enabled(self._enable_shell, "AwaitShell")
        timeout_s = max(0, block_until_ms) / 1000.0

        if shell_id is None:
            time.sleep(min(timeout_s, 10))
            return f"Slept {timeout_s:.1f}s"

        registry = JobRegistry.get()
        if pattern:
            import re
            rx = re.compile(pattern)
            deadline = time.time() + timeout_s
            while time.time() < deadline:
                job = registry.poll(shell_id)
                if job is None:
                    return f"Unknown job: {shell_id}"
                out = job.get_output()
                if rx.search(out):
                    return self._job_summary(job)
                if not job.running:
                    return self._job_summary(job)
                time.sleep(0.3)
            job = registry.poll(shell_id)
            return self._job_summary(job) if job else f"Unknown job: {shell_id}"

        job = registry.wait(shell_id, timeout=timeout_s)
        if job is None:
            return f"Unknown job: {shell_id}"
        return self._job_summary(job)

    def _job_summary(self, job: Any) -> str:
        elapsed = time.time() - job.started_at
        out = job.get_output()
        status = "running" if job.running else f"exit_code={job.exit_code}"
        return (
            f"job_id={job.id} status={status} elapsed={elapsed:.1f}s\n"
            f"command: {job.command}\n"
            f"output:\n{out[-6000:]}"
        )

    # ══════════════════════════════════════════════════════════════════════
    # META TOOLS
    # ══════════════════════════════════════════════════════════════════════

    def todo_write(self, todos: list, merge: bool = False, agent: Any = None) -> str:
        """Create or update the agent's structured task list.

        Args:
            todos (list): Array of TODO items with ``id``, ``content``, ``status``.
            merge (bool): Merge into existing list if True; replace if False.
            agent: Buddy agent (auto-injected).

        Returns:
            str: Confirmation message.
        """
        validated = []
        for t in todos:
            if not isinstance(t, dict):
                continue
            validated.append({
                "id": str(t.get("id", "")),
                "content": t.get("content", ""),
                "status": t.get("status", "pending"),
            })

        # Store in session state if agent available
        if agent is not None and hasattr(agent, "session_state"):
            if agent.session_state is None:
                agent.session_state = {}
            if merge:
                existing: list = agent.session_state.get("todos", [])
                by_id = {t["id"]: t for t in existing}
                for t in validated:
                    if t["id"] in by_id:
                        by_id[t["id"]].update(t)
                    else:
                        by_id[t["id"]] = t
                agent.session_state["todos"] = list(by_id.values())
            else:
                agent.session_state["todos"] = validated

        # Emit SSE event to UI
        self._emit("todo_update", {
            "todos": (agent.session_state.get("todos", []) if (agent is not None and hasattr(agent, "session_state") and agent.session_state and merge) else validated),
        })

        # Remove old manual emit
        return json.dumps({"updated": len(validated), "mode": "merge" if merge else "replace"})

    def edit_notebook(
        self,
        target_notebook: str,
        cell_idx: int,
        is_new_cell: bool,
        cell_language: str,
        old_string: str,
        new_string: str,
    ) -> str:
        """Edit or create a cell in a Jupyter notebook.

        Args:
            target_notebook (str): Workspace-relative path to the .ipynb file.
            cell_idx (int): 0-based cell index.
            is_new_cell (bool): Create a new cell at cell_idx if True; edit existing if False.
            cell_language (str): Language for new cells (``python``, ``markdown``, etc.).
            old_string (str): String to replace (ignored when is_new_cell=True).
            new_string (str): Replacement text or new cell content.

        Returns:
            str: Confirmation message.
        """
        self._mutating_check()
        import copy
        p = self._sb.resolve(target_notebook)
        if not p.exists():
            return f"Error: {target_notebook} not found"
        try:
            nb = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            return f"Error reading notebook: {e}"

        cells = nb.get("cells", [])
        lang_to_type = {"markdown": "markdown", "raw": "raw"}
        cell_type = lang_to_type.get(cell_language, "code")

        if is_new_cell:
            new_cell: dict = {
                "cell_type": cell_type,
                "metadata": {},
                "source": new_string.splitlines(keepends=True),
            }
            if cell_type == "code":
                new_cell["outputs"] = []
                new_cell["execution_count"] = None
            cells.insert(cell_idx, new_cell)
            nb["cells"] = cells
        else:
            if cell_idx >= len(cells):
                return f"Error: cell_idx {cell_idx} out of range (notebook has {len(cells)} cells)"
            cell = copy.deepcopy(cells[cell_idx])
            src = "".join(cell.get("source", []))
            if old_string not in src:
                return f"Error: old_string not found in cell {cell_idx}"
            new_src = src.replace(old_string, new_string, 1)
            cell["source"] = new_src.splitlines(keepends=True)
            cells[cell_idx] = cell
            nb["cells"] = cells

        p.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
        action = "Created new" if is_new_cell else "Edited"
        return f"{action} cell {cell_idx} in {self._sb.rel(p)}"

    def read_lints(self, paths: Optional[list] = None) -> str:
        """Read linter diagnostics for the specified files (or all files if omitted).

        Args:
            paths (list): Optional list of file paths to restrict results.

        Returns:
            str: JSON array of diagnostic objects with path, line, severity, message.
        """
        try:
            from buddy.code.server._diagnostics import get_diagnostics
            diags = get_diagnostics()
        except ImportError:
            diags = []

        if paths:
            diags = [d for d in diags if any(d.get("path", "").endswith(p) or p in d.get("path", "") for p in paths)]

        if not diags:
            return "No diagnostics found."
        return json.dumps(diags, indent=2)

    # ══════════════════════════════════════════════════════════════════════
    # MODE TOOLS
    # ══════════════════════════════════════════════════════════════════════

    def switch_mode(self, target_mode_id: str, explanation: Optional[str] = None, agent: Any = None) -> str:
        """Switch the interaction mode.

        Args:
            target_mode_id (str): ``"agent"`` | ``"plan"`` | ``"ask"``.
            explanation (str): Optional explanation shown to the user.
            agent: Buddy agent (auto-injected).

        Returns:
            str: Confirmation.
        """
        allowed = {"agent", "plan", "ask"}
        if target_mode_id not in allowed:
            return f"Error: unknown mode '{target_mode_id}'. Choose from: {', '.join(allowed)}"
        self._mode = target_mode_id

        if agent is not None and hasattr(agent, "session_state"):
            if agent.session_state is None:
                agent.session_state = {}
            agent.session_state["mode"] = target_mode_id

        self._emit("mode_switch", {"mode": target_mode_id, "explanation": explanation})
        return f"Switched to {target_mode_id} mode." + (f" {explanation}" if explanation else "")

    def create_plan(
        self,
        name: str,
        overview: str,
        todos: Optional[list] = None,
        is_project: bool = False,
        agent: Any = None,
    ) -> str:
        """Create a structured implementation plan and surface it to the user.

        Args:
            name (str): Short name for the plan.
            overview (str): 1-3 sentence description of what the plan achieves.
            todos (list): Optional list of TODO items to seed the plan.
            is_project (bool): Whether this plan is a long-running project.
            agent: Buddy agent (auto-injected).

        Returns:
            str: Markdown plan text.
        """
        todo_block = ""
        if todos:
            todo_block = "\n".join(
                f"- [ ] {t['content'] if isinstance(t, dict) else t}" for t in todos
            )

        plan_md = f"# {name}\n\n{overview}\n"
        if todo_block:
            plan_md += f"\n## Tasks\n\n{todo_block}\n"

        if agent is not None and hasattr(agent, "session_state"):
            if agent.session_state is None:
                agent.session_state = {}
            agent.session_state["plan"] = {"name": name, "overview": overview, "todos": todos or []}

        self._emit("plan_created", {
            "plan": {
                "name": name,
                "overview": overview,
                "plan": plan_md,
                "todos": todos or [],
            }
        })

        # Also update todos if provided
        if todos and agent is not None:
            self.todo_write(todos, merge=False, agent=agent)

        return plan_md

    def ask_question(
        self,
        title: Optional[str] = None,
        questions: Optional[list] = None,
        agent: Any = None,
    ) -> str:
        """Pause the agent loop and ask the user a structured question.

        Args:
            title (str): Optional title for the question form.
            questions (list): Array of question objects with ``id``, ``prompt``,
                ``options`` (``[{id, label}]``), and optional ``allow_multiple``.
            agent: Buddy agent (auto-injected).

        Returns:
            str: The user's answer(s) as JSON.
        """
        if not questions:
            return "Error: questions list is required"

        payload = {"title": title, "questions": questions}
        self._emit("ask_question", {"payload": payload})

        # Block this thread until the UI sends back answers
        if self._session_id:
            try:
                from buddy.code.server._events import wait_answer
                answers = wait_answer(self._session_id, timeout=300)
                if answers is not None:
                    return json.dumps(answers)
            except Exception:
                pass

        return json.dumps({"status": "no_answer"})

    # ══════════════════════════════════════════════════════════════════════
    # TASK SUBAGENTS
    # ══════════════════════════════════════════════════════════════════════

    def task(
        self,
        description: str,
        prompt: str,
        subagent_type: str = "generalPurpose",
        run_in_background: bool = False,
        agent: Any = None,
    ) -> str:
        """Launch a sub-agent to handle a complex task autonomously.

        Args:
            description (str): Short title for the sub-agent (3-5 words).
            prompt (str): Detailed task instructions for the sub-agent.
            subagent_type (str): One of ``generalPurpose``, ``explore``, ``shell``.
            run_in_background (bool): Return immediately without waiting.
            agent: Buddy agent (auto-injected).

        Returns:
            str: Sub-agent result or job info.
        """
        if agent is None:
            return "Error: Task requires an agent context."

        supported = {"generalPurpose", "explore", "shell"}
        if subagent_type not in supported:
            subagent_type = "generalPurpose"

        # Build a child agent using the same model/tools
        try:
            from buddy.agent import Agent
            child_tools = CursorTools(
                base_path=str(self._sb.base),
                enable_shell=self._enable_shell,
                mode="agent",
            )
            child_agent = Agent(
                name=f"SubAgent-{subagent_type}",
                instructions=(
                    f"You are a sub-agent specializing in: {subagent_type}. "
                    "Complete the assigned task and return a concise result."
                ),
                tools=[child_tools],
                model=getattr(agent, 'model', None),
                session_id=f"sub_{int(time.time())}",
            )

            if run_in_background:
                import threading
                result_holder: list = []
                def run():
                    try:
                        resp = child_agent.run(prompt)
                        result_holder.append(str(resp))
                    except Exception as e:
                        result_holder.append(f"Error: {e}")
                t = threading.Thread(target=run, daemon=True)
                t.start()
                return f"Sub-agent '{description}' started in background."

            resp = child_agent.run(prompt)
            return str(resp)
        except Exception as e:
            # Fallback: just run Shell if it's a shell sub-agent
            if subagent_type == "shell" and self._enable_shell:
                return self.shell(prompt)
            return f"Task error: {e}"

    # ══════════════════════════════════════════════════════════════════════
    # MCP DYNAMIC TOOLS
    # ══════════════════════════════════════════════════════════════════════

    def _load_mcp_config(self) -> Dict[str, Any]:
        """Load .aura/mcp.json from the workspace root."""
        cfg_path = self._sb.base / ".aura" / "mcp.json"
        if cfg_path.exists():
            try:
                data = json.loads(cfg_path.read_text(encoding="utf-8"))
                # Support both {"servers": {...}} and {"mcpServers": {...}} formats
                return data.get("servers", data.get("mcpServers", data))
            except Exception:
                pass
        return {}

    def _run_async(self, coro):
        """Run an async coroutine from sync context, handling existing event loops."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Use a new thread with its own event loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    fut = pool.submit(asyncio.run, coro)
                    return fut.result(timeout=60)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    async def _mcp_list_tools(self, server_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Async: connect to MCP server and list its tools."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from mcp.client.streamable_http import streamablehttp_client
        from contextlib import AsyncExitStack

        url = server_cfg.get("url") or server_cfg.get("serverUrl")
        command = server_cfg.get("command")
        args = server_cfg.get("args", [])
        env = server_cfg.get("env", {})
        transport = server_cfg.get("transport", "streamable-http" if url else "stdio")

        async with AsyncExitStack() as stack:
            if transport in ("streamable-http", "sse") and url:
                client_ctx = streamablehttp_client(url)
                read, write, _ = await stack.enter_async_context(client_ctx)
            elif command:
                server_params = StdioServerParameters(
                    command=command, args=args, env=env or None
                )
                read, write = await stack.enter_async_context(stdio_client(server_params))
            else:
                return []

            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            resp = await session.list_tools()
            tools = []
            for t in resp.tools:
                tools.append({
                    "name": t.name,
                    "description": t.description or "",
                    "inputSchema": t.inputSchema if hasattr(t, "inputSchema") else {},
                })
            return tools

    async def _mcp_call_tool(self, server_cfg: Dict[str, Any], tool_name: str, arguments: Dict[str, Any]) -> str:
        """Async: connect to MCP server and call a tool."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from mcp.client.streamable_http import streamablehttp_client
        from contextlib import AsyncExitStack

        url = server_cfg.get("url") or server_cfg.get("serverUrl")
        command = server_cfg.get("command")
        args = server_cfg.get("args", [])
        env = server_cfg.get("env", {})
        transport = server_cfg.get("transport", "streamable-http" if url else "stdio")

        async with AsyncExitStack() as stack:
            if transport in ("streamable-http", "sse") and url:
                client_ctx = streamablehttp_client(url)
                read, write, _ = await stack.enter_async_context(client_ctx)
            elif command:
                server_params = StdioServerParameters(
                    command=command, args=args, env=env or None
                )
                read, write = await stack.enter_async_context(stdio_client(server_params))
            else:
                return "Error: no transport configured"

            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            parts = []
            for c in result.content:
                if hasattr(c, "text"):
                    parts.append(c.text)
                else:
                    parts.append(str(c))
            return "\n".join(parts) or "(empty result)"

    async def _mcp_fetch_resource(self, server_cfg: Dict[str, Any], uri: str) -> str:
        """Async: connect to MCP server and fetch a resource."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from mcp.client.streamable_http import streamablehttp_client
        from contextlib import AsyncExitStack

        url = server_cfg.get("url") or server_cfg.get("serverUrl")
        command = server_cfg.get("command")
        args = server_cfg.get("args", [])
        env = server_cfg.get("env", {})
        transport = server_cfg.get("transport", "streamable-http" if url else "stdio")

        async with AsyncExitStack() as stack:
            if transport in ("streamable-http", "sse") and url:
                client_ctx = streamablehttp_client(url)
                read, write, _ = await stack.enter_async_context(client_ctx)
            elif command:
                server_params = StdioServerParameters(
                    command=command, args=args, env=env or None
                )
                read, write = await stack.enter_async_context(stdio_client(server_params))
            else:
                return "Error: no transport configured"

            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            result = await session.read_resource(uri)
            parts = []
            for c in result.contents:
                if hasattr(c, "text"):
                    parts.append(c.text)
                else:
                    parts.append(str(c))
            return "\n".join(parts) or "(empty resource)"

    def get_dynamic_tools(self, namespace: str) -> str:
        """Discover available tools from a named MCP server configured in .aura/mcp.json.

        Args:
            namespace (str): Name of the MCP server as configured in .aura/mcp.json.

        Returns:
            str: JSON array of tool schemas with name, description, and inputSchema.
        """
        servers = self._load_mcp_config()
        if namespace not in servers:
            available = list(servers.keys())
            return f"Error: MCP server '{namespace}' not found. Available: {available}"
        server_cfg = servers[namespace]
        if not server_cfg.get("enabled", True):
            return f"Error: MCP server '{namespace}' is disabled."
        try:
            tools = self._run_async(self._mcp_list_tools(server_cfg))
            return json.dumps(tools, indent=2)
        except Exception as e:
            return f"Error listing tools from '{namespace}': {e}"

    def call_dynamic_tool(
        self,
        namespace: str,
        toolName: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Invoke a tool on a named MCP server configured in .aura/mcp.json.

        Args:
            namespace (str): Name of the MCP server.
            toolName (str): Name of the tool to invoke.
            arguments (dict): Arguments to pass to the tool.

        Returns:
            str: Tool result as text.
        """
        servers = self._load_mcp_config()
        if namespace not in servers:
            return f"Error: MCP server '{namespace}' not found."
        server_cfg = servers[namespace]
        if not server_cfg.get("enabled", True):
            return f"Error: MCP server '{namespace}' is disabled."
        try:
            return self._run_async(self._mcp_call_tool(server_cfg, toolName, arguments or {}))
        except Exception as e:
            return f"Error calling '{toolName}' on '{namespace}': {e}"

    def fetch_mcp_resource(self, server: str, uri: str) -> str:
        """Read a resource from a named MCP server configured in .aura/mcp.json.

        Args:
            server (str): Name of the MCP server.
            uri (str): Resource URI to fetch.

        Returns:
            str: Resource content as text.
        """
        servers = self._load_mcp_config()
        if server not in servers:
            return f"Error: MCP server '{server}' not found."
        server_cfg = servers[server]
        if not server_cfg.get("enabled", True):
            return f"Error: MCP server '{server}' is disabled."
        try:
            return self._run_async(self._mcp_fetch_resource(server_cfg, uri))
        except Exception as e:
            return f"Error fetching resource '{uri}' from '{server}': {e}"

    # ══════════════════════════════════════════════════════════════════════
    # BROWSER TOOLS (Playwright)
    # ══════════════════════════════════════════════════════════════════════

    def _get_browser_page(self):
        """Get or create the shared Playwright browser page for this session."""
        if not hasattr(self, "_browser_page") or self._browser_page is None:
            raise RuntimeError(
                "Browser not initialized. Call browser_navigate() first to open a page."
            )
        return self._browser_page

    def _init_browser_sync(self) -> None:
        """Initialize Playwright browser synchronously (first call only)."""
        if hasattr(self, "_browser_pw") and self._browser_pw is not None:
            return
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        self._browser_pw = pw
        self._browser_obj = browser
        self._browser_ctx = ctx
        self._browser_page = page
        self._browser_refs: Dict[str, Any] = {}  # opaque ref -> locator/element

    def browser_navigate(self, url: str, wait_until: str = "load") -> str:
        """Navigate the browser to a URL.

        Args:
            url (str): URL to navigate to.
            wait_until (str): When to consider navigation done: ``"load"``, ``"domcontentloaded"``, ``"networkidle"``.

        Returns:
            str: Page title and URL after navigation.
        """
        self._sb.assert_enabled(self._enable_browser, "browser_navigate")
        self._init_browser_sync()
        page = self._browser_page
        try:
            page.goto(url, wait_until=wait_until, timeout=30000)
            return f"Navigated to: {page.url}\nTitle: {page.title()}"
        except Exception as e:
            return f"Navigation error: {e}"

    def browser_snapshot(self) -> str:
        """Capture an accessibility tree snapshot of the current page.

        Returns:
            str: YAML-like accessibility tree with opaque refs for interactive elements.
        """
        self._sb.assert_enabled(self._enable_browser, "browser_snapshot")
        page = self._get_browser_page()
        try:
            # Build accessibility tree using CDP
            result = page.accessibility.snapshot()
            if not result:
                return "Page is empty or not loaded."
            refs: Dict[str, Any] = {}

            def _fmt(node: dict, depth: int = 0) -> List[str]:
                lines = []
                indent = "  " * depth
                role = node.get("role", "unknown")
                name = node.get("name", "")
                value = node.get("value", "")
                checked = node.get("checked")
                focused = node.get("focused")

                parts = [f"{indent}- role: {role}"]
                if name:
                    parts.append(f"  name: {name!r}")
                if value:
                    parts.append(f"  value: {value!r}")
                if checked is not None:
                    parts.append(f"  checked: {checked}")
                if focused:
                    parts.append(f"  focused: true")

                # Generate ref for interactive elements
                interactive_roles = {
                    "button", "link", "textbox", "combobox", "checkbox",
                    "radio", "menuitem", "option", "listitem", "tab",
                    "treeitem", "gridcell",
                }
                if role in interactive_roles and name:
                    ref_id = f"r{len(refs)}"
                    refs[ref_id] = {"role": role, "name": name}
                    parts.append(f"  ref: {ref_id}")

                lines.append("\n".join(parts))
                for child in node.get("children", []):
                    lines.extend(_fmt(child, depth + 1))
                return lines

            tree_lines = _fmt(result)
            self._browser_refs = refs
            return f"Page: {page.url}\n---\n" + "\n".join(tree_lines)
        except Exception as e:
            return f"Snapshot error: {e}"

    def _resolve_ref(self, ref: str):
        """Resolve an opaque ref to a Playwright locator."""
        refs = getattr(self, "_browser_refs", {})
        if ref not in refs:
            return None
        info = refs[ref]
        page = self._browser_page
        role = info.get("role", "")
        name = info.get("name", "")
        try:
            return page.get_by_role(role, name=name)
        except Exception:
            return None

    def browser_click(self, ref: str) -> str:
        """Click an element identified by its ref from the last snapshot.

        Args:
            ref (str): Opaque ref from browser_snapshot output.

        Returns:
            str: Confirmation or error.
        """
        self._sb.assert_enabled(self._enable_browser, "browser_click")
        page = self._get_browser_page()
        loc = self._resolve_ref(ref)
        if loc is None:
            return f"Error: ref '{ref}' not found. Run browser_snapshot() first."
        try:
            loc.click(timeout=5000)
            return f"Clicked ref={ref}"
        except Exception as e:
            return f"Click error: {e}"

    def browser_type(self, ref: str, text: str) -> str:
        """Type text into a focused element identified by its ref.

        Args:
            ref (str): Opaque ref from browser_snapshot output.
            text (str): Text to type.

        Returns:
            str: Confirmation or error.
        """
        self._sb.assert_enabled(self._enable_browser, "browser_type")
        page = self._get_browser_page()
        loc = self._resolve_ref(ref)
        if loc is None:
            return f"Error: ref '{ref}' not found. Run browser_snapshot() first."
        try:
            loc.type(text, timeout=5000)
            return f"Typed {len(text)} chars into ref={ref}"
        except Exception as e:
            return f"Type error: {e}"

    def browser_fill(self, ref: str, value: str) -> str:
        """Fill an input field identified by its ref (replaces existing value).

        Args:
            ref (str): Opaque ref from browser_snapshot output.
            value (str): Value to fill.

        Returns:
            str: Confirmation or error.
        """
        self._sb.assert_enabled(self._enable_browser, "browser_fill")
        page = self._get_browser_page()
        loc = self._resolve_ref(ref)
        if loc is None:
            return f"Error: ref '{ref}' not found. Run browser_snapshot() first."
        try:
            loc.fill(value, timeout=5000)
            return f"Filled ref={ref} with {len(value)} chars"
        except Exception as e:
            return f"Fill error: {e}"

    def browser_press_key(self, key: str) -> str:
        """Press a keyboard key on the focused element.

        Args:
            key (str): Key name (e.g. ``"Enter"``, ``"Escape"``, ``"ArrowDown"``, ``"Control+a"``).

        Returns:
            str: Confirmation or error.
        """
        self._sb.assert_enabled(self._enable_browser, "browser_press_key")
        page = self._get_browser_page()
        try:
            page.keyboard.press(key)
            return f"Pressed key: {key}"
        except Exception as e:
            return f"Key error: {e}"

    def browser_scroll(self, direction: str = "down", amount: int = 3) -> str:
        """Scroll the page.

        Args:
            direction (str): ``"up"``, ``"down"``, ``"left"``, ``"right"``.
            amount (int): Number of scroll steps (each step ~100px).

        Returns:
            str: Confirmation.
        """
        self._sb.assert_enabled(self._enable_browser, "browser_scroll")
        page = self._get_browser_page()
        delta_map = {
            "down":  (0,   100 * amount),
            "up":    (0,  -100 * amount),
            "right": (100 * amount, 0),
            "left":  (-100 * amount, 0),
        }
        dx, dy = delta_map.get(direction, (0, 100 * amount))
        try:
            page.mouse.wheel(dx, dy)
            return f"Scrolled {direction} by {amount} steps"
        except Exception as e:
            return f"Scroll error: {e}"

    def browser_take_screenshot(self) -> str:
        """Take a screenshot of the current page.

        Returns:
            str: File path where the screenshot was saved.
        """
        self._sb.assert_enabled(self._enable_browser, "browser_take_screenshot")
        page = self._get_browser_page()
        import tempfile
        try:
            out = Path(tempfile.mktemp(suffix=".png", prefix="aura_browser_"))
            page.screenshot(path=str(out), full_page=False)
            return f"Screenshot saved: {out}"
        except Exception as e:
            return f"Screenshot error: {e}"

    def browser_tabs(self, action: str = "list", url: Optional[str] = None) -> str:
        """Manage browser tabs.

        Args:
            action (str): ``"list"`` | ``"new"`` | ``"close"``.
            url (str): URL for ``"new"`` action.

        Returns:
            str: Tab info or confirmation.
        """
        self._sb.assert_enabled(self._enable_browser, "browser_tabs")
        if action == "list":
            if not hasattr(self, "_browser_ctx") or self._browser_ctx is None:
                return "No browser session active."
            pages = self._browser_ctx.pages
            lines = [f"[{i}] {p.url} — {p.title()}" for i, p in enumerate(pages)]
            return "\n".join(lines) or "No tabs open."
        elif action == "new":
            self._init_browser_sync()
            new_page = self._browser_ctx.new_page()
            self._browser_page = new_page
            if url:
                new_page.goto(url, timeout=30000)
            return f"Opened new tab: {new_page.url}"
        elif action == "close":
            if hasattr(self, "_browser_page") and self._browser_page:
                self._browser_page.close()
                pages = self._browser_ctx.pages
                self._browser_page = pages[-1] if pages else None
                return "Closed current tab."
            return "No active tab."
        else:
            return f"Unknown action '{action}'. Use: list, new, close"
