"""Batch processing for LLM requests.

This module provides a unified batch processing interface across providers:

* **Anthropic Message Batches API** – asynchronous, 50% cost discount,
  up to 100k requests or 256 MB per batch.
* **OpenAI Batch API** – asynchronous, 50% cost discount for supported models.
* **Generic BatchRunner** – runs any Buddy model in parallel threads/async
  tasks, useful for models without a native batch API.

Usage (Anthropic)::

    from buddy.models.batch import AnthropicBatchProcessor

    processor = AnthropicBatchProcessor(api_key="sk-ant-...")
    batch_id = processor.create_batch([
        {"custom_id": "req-1", "params": {"model": "claude-opus-5", "max_tokens": 1024,
          "messages": [{"role": "user", "content": "Hello"}]}},
        {"custom_id": "req-2", "params": {"model": "claude-opus-5", "max_tokens": 1024,
          "messages": [{"role": "user", "content": "Goodbye"}]}},
    ])
    results = processor.wait_and_collect(batch_id)

Usage (generic runner)::

    from buddy.models.batch import BatchRunner
    from buddy.models.anthropic import Claude

    runner = BatchRunner(model=Claude(id="claude-opus-5"))
    results = runner.run_batch([
        "Translate 'Hello' to Spanish",
        "Translate 'Hello' to French",
    ])

References
----------
* https://platform.claude.com/docs/en/build-with-claude/batch-processing
* https://platform.openai.com/docs/guides/batch
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional, Union

from buddy.utils.log import log_debug, log_error, log_info, log_warning

# ── Shared types ─────────────────────────────────────────────────────────────

BatchStatus = str   # "in_progress" | "ended" | "expired" | "canceling" | "canceled"


@dataclass
class BatchResult:
    """Result for a single request in a batch."""

    custom_id: str
    result_type: str   # "succeeded" | "errored" | "expired" | "canceled"
    content: Optional[str] = None         # extracted text content (convenience)
    raw_response: Optional[Any] = None    # full provider response object
    error: Optional[str] = None
    stop_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None

    @property
    def succeeded(self) -> bool:
        return self.result_type == "succeeded"

    @property
    def is_refusal(self) -> bool:
        return self.stop_reason == "refusal"


# ── Anthropic Batch Processor ─────────────────────────────────────────────────

class AnthropicBatchProcessor:
    """Submit and manage Anthropic Message Batches.

    Limitations
    -----------
    * Max 100,000 requests or 256 MB per batch.
    * Results available for 29 days.
    * ``stream=True`` and ``speed="fast"`` are NOT supported.
    * Each request must have ``max_tokens >= 1``.

    Args:
        api_key: Anthropic API key.  Defaults to the ``ANTHROPIC_API_KEY``
            environment variable.
        poll_interval: Seconds between status polls when calling
            :meth:`wait_and_collect`.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        poll_interval: float = 30.0,
    ) -> None:
        try:
            from anthropic import Anthropic as AnthropicClient
        except ImportError as e:
            raise ImportError(
                "`anthropic` is not installed.  Install with `pip install anthropic`."
            ) from e

        import os
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = AnthropicClient(api_key=self._api_key)
        self.poll_interval = poll_interval

    def create_batch(
        self,
        requests: List[Dict[str, Any]],
    ) -> str:
        """Submit a batch and return the batch ID.

        Each item in *requests* must have:
            ``custom_id``: unique per-request identifier.
            ``params``: dict of Messages API parameters (model, max_tokens,
                messages, …).  Do NOT include ``stream``.

        Returns the ``batch_id`` string.
        """
        batch_requests = []
        for req in requests:
            custom_id = req.get("custom_id") or req.get("id", f"req-{len(batch_requests)}")
            params = req.get("params", req)
            # Strip unsupported batch params
            params = {k: v for k, v in params.items()
                      if k not in ("stream", "speed", "store", "previous_thread_event_id")}
            batch_requests.append({"custom_id": custom_id, "params": params})

        log_info(f"AnthropicBatch: submitting {len(batch_requests)} requests")
        batch = self._client.messages.batches.create(requests=batch_requests)
        log_info(f"AnthropicBatch: created batch {batch.id!r}")
        return batch.id

    def get_status(self, batch_id: str) -> Dict[str, Any]:
        """Return status dict for *batch_id*."""
        batch = self._client.messages.batches.retrieve(batch_id)
        return {
            "id": batch.id,
            "status": batch.processing_status,
            "request_counts": getattr(batch, "request_counts", {}),
            "expires_at": getattr(batch, "expires_at", None),
        }

    def wait_and_collect(
        self,
        batch_id: str,
        timeout_seconds: float = 3600.0,
    ) -> List[BatchResult]:
        """Poll until the batch ends, then collect and return all results.

        Raises ``TimeoutError`` if the batch has not ended within
        *timeout_seconds*.
        """
        deadline = time.monotonic() + timeout_seconds
        while True:
            status = self.get_status(batch_id)
            processing_status = status.get("status", "")
            log_debug(f"AnthropicBatch {batch_id!r}: status={processing_status}")
            if processing_status == "ended":
                break
            if processing_status in ("expired", "canceled"):
                raise RuntimeError(
                    f"Batch {batch_id!r} ended with status {processing_status!r}"
                )
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Batch {batch_id!r} did not finish within {timeout_seconds}s"
                )
            time.sleep(self.poll_interval)

        return self._collect_results(batch_id)

    def _collect_results(self, batch_id: str) -> List[BatchResult]:
        results: List[BatchResult] = []
        for item in self._client.messages.batches.results(batch_id):
            result_type = item.result.type if hasattr(item.result, "type") else "errored"
            content = None
            stop_reason = None
            usage = None
            error = None
            raw = item.result

            if result_type == "succeeded":
                msg = getattr(item.result, "message", None)
                if msg:
                    for block in getattr(msg, "content", []):
                        if getattr(block, "type", "") == "text":
                            content = block.text
                            break
                    stop_reason = getattr(msg, "stop_reason", None)
                    raw_usage = getattr(msg, "usage", None)
                    if raw_usage:
                        usage = {
                            "input_tokens": getattr(raw_usage, "input_tokens", 0),
                            "output_tokens": getattr(raw_usage, "output_tokens", 0),
                        }
            elif result_type == "errored":
                err = getattr(item.result, "error", None)
                error = str(err) if err else "unknown error"

            results.append(BatchResult(
                custom_id=item.custom_id,
                result_type=result_type,
                content=content,
                raw_response=raw,
                error=error,
                stop_reason=stop_reason,
                usage=usage,
            ))
        return results

    async def acreate_batch(self, requests: List[Dict[str, Any]]) -> str:
        """Async version of :meth:`create_batch`."""
        try:
            from anthropic import AsyncAnthropic
        except ImportError as e:
            raise ImportError("`anthropic` not installed.") from e

        import os
        async_client = AsyncAnthropic(api_key=self._api_key)
        batch_requests = []
        for req in requests:
            custom_id = req.get("custom_id") or req.get("id", f"req-{len(batch_requests)}")
            params = req.get("params", req)
            params = {k: v for k, v in params.items()
                      if k not in ("stream", "speed", "store", "previous_thread_event_id")}
            batch_requests.append({"custom_id": custom_id, "params": params})

        batch = await async_client.messages.batches.create(requests=batch_requests)
        return batch.id

    async def await_and_collect(
        self,
        batch_id: str,
        timeout_seconds: float = 3600.0,
    ) -> List[BatchResult]:
        """Async version of :meth:`wait_and_collect`."""
        import asyncio
        try:
            from anthropic import AsyncAnthropic
        except ImportError as e:
            raise ImportError("`anthropic` not installed.") from e

        async_client = AsyncAnthropic(api_key=self._api_key)
        deadline = time.monotonic() + timeout_seconds
        while True:
            batch = await async_client.messages.batches.retrieve(batch_id)
            status = batch.processing_status
            if status == "ended":
                break
            if status in ("expired", "canceled"):
                raise RuntimeError(f"Batch {batch_id!r} ended with status {status!r}")
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Batch {batch_id!r} did not finish within {timeout_seconds}s")
            await asyncio.sleep(self.poll_interval)

        results: List[BatchResult] = []
        async for item in await async_client.messages.batches.results(batch_id):
            result_type = item.result.type if hasattr(item.result, "type") else "errored"
            content = None
            stop_reason = None
            error = None
            usage = None

            if result_type == "succeeded":
                msg = getattr(item.result, "message", None)
                if msg:
                    for block in getattr(msg, "content", []):
                        if getattr(block, "type", "") == "text":
                            content = block.text
                            break
                    stop_reason = getattr(msg, "stop_reason", None)
                    raw_usage = getattr(msg, "usage", None)
                    if raw_usage:
                        usage = {
                            "input_tokens": getattr(raw_usage, "input_tokens", 0),
                            "output_tokens": getattr(raw_usage, "output_tokens", 0),
                        }
            elif result_type == "errored":
                err = getattr(item.result, "error", None)
                error = str(err) if err else "unknown error"

            results.append(BatchResult(
                custom_id=item.custom_id,
                result_type=result_type,
                content=content,
                raw_response=item.result,
                error=error,
                stop_reason=stop_reason,
                usage=usage,
            ))
        return results


# ── OpenAI Batch Processor ────────────────────────────────────────────────────

class OpenAIBatchProcessor:
    """Submit and manage OpenAI Batch API jobs.

    Supports chat completions and embeddings.  Costs 50% less than the
    standard API for supported models.

    Args:
        api_key: OpenAI API key.  Defaults to the ``OPENAI_API_KEY`` env var.
        poll_interval: Seconds between status polls.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        poll_interval: float = 60.0,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "`openai` not installed.  Install with `pip install openai`."
            ) from e

        import os
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = OpenAI(api_key=self._api_key)
        self.poll_interval = poll_interval

    def create_batch(
        self,
        requests: List[Dict[str, Any]],
        endpoint: str = "/v1/chat/completions",
        completion_window: str = "24h",
    ) -> str:
        """Submit a batch and return the batch ID.

        Each item in *requests* must have:
            ``custom_id``: unique per-request identifier.
            ``method``: HTTP method (default ``"POST"``).
            ``url``: endpoint path (default ``endpoint`` arg).
            ``body``: request body dict (model, messages, …).

        Returns the batch ID.
        """
        import io
        # Build JSONL content
        lines = []
        for req in requests:
            custom_id = req.get("custom_id", f"req-{len(lines)}")
            body = req.get("body", req.get("params", req))
            line = {
                "custom_id": custom_id,
                "method": req.get("method", "POST"),
                "url": req.get("url", endpoint),
                "body": body,
            }
            lines.append(json.dumps(line))

        jsonl_bytes = "\n".join(lines).encode()
        file_response = self._client.files.create(
            file=("batch_requests.jsonl", io.BytesIO(jsonl_bytes), "application/jsonl"),
            purpose="batch",
        )

        batch = self._client.batches.create(
            input_file_id=file_response.id,
            endpoint=endpoint,
            completion_window=completion_window,
        )
        log_info(f"OpenAIBatch: created batch {batch.id!r}")
        return batch.id

    def get_status(self, batch_id: str) -> Dict[str, Any]:
        batch = self._client.batches.retrieve(batch_id)
        return {
            "id": batch.id,
            "status": batch.status,
            "request_counts": getattr(batch, "request_counts", {}),
            "expires_at": getattr(batch, "expires_at", None),
        }

    def wait_and_collect(
        self,
        batch_id: str,
        timeout_seconds: float = 86400.0,
    ) -> List[BatchResult]:
        """Poll until the batch completes, then collect and return results."""
        deadline = time.monotonic() + timeout_seconds
        while True:
            status = self.get_status(batch_id)
            st = status.get("status", "")
            log_debug(f"OpenAIBatch {batch_id!r}: status={st}")
            if st == "completed":
                break
            if st in ("failed", "expired", "cancelled"):
                raise RuntimeError(
                    f"OpenAI Batch {batch_id!r} ended with status {st!r}"
                )
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"OpenAI Batch {batch_id!r} did not finish within {timeout_seconds}s"
                )
            time.sleep(self.poll_interval)

        return self._collect_results(batch_id)

    def _collect_results(self, batch_id: str) -> List[BatchResult]:
        batch = self._client.batches.retrieve(batch_id)
        if not batch.output_file_id:
            return []
        content = self._client.files.content(batch.output_file_id)
        results: List[BatchResult] = []
        for line in content.text.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            custom_id = obj.get("custom_id", "")
            resp = obj.get("response", {})
            error = obj.get("error")
            result_type = "succeeded" if resp else "errored"
            text_content = None
            stop_reason = None
            usage = None

            if result_type == "succeeded":
                body = resp.get("body", {})
                choices = body.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    text_content = msg.get("content")
                    stop_reason = choices[0].get("finish_reason")
                usage_raw = body.get("usage", {})
                if usage_raw:
                    usage = {
                        "input_tokens": usage_raw.get("prompt_tokens", 0),
                        "output_tokens": usage_raw.get("completion_tokens", 0),
                    }

            results.append(BatchResult(
                custom_id=custom_id,
                result_type=result_type,
                content=text_content,
                raw_response=obj,
                error=str(error) if error else None,
                stop_reason=stop_reason,
                usage=usage,
            ))
        return results


# ── Generic Batch Runner ──────────────────────────────────────────────────────

class BatchRunner:
    """Run a list of prompts through any Buddy Model in parallel.

    Unlike :class:`AnthropicBatchProcessor` and :class:`OpenAIBatchProcessor`,
    this runner works with **any** Buddy model.  It uses a thread pool for
    synchronous models or ``asyncio.gather`` for async models.

    Args:
        model: A Buddy ``Model`` instance.
        max_workers: Maximum parallel threads for sync execution.
    """

    def __init__(self, model: Any, max_workers: int = 10) -> None:
        self.model = model
        self.max_workers = max_workers

    def run_batch(
        self,
        prompts: List[Union[str, Dict[str, Any]]],
        system_prompt: Optional[str] = None,
    ) -> List[BatchResult]:
        """Run all prompts and return results.

        Each item in *prompts* can be:
            * A plain string prompt.
            * A dict with ``custom_id`` and ``prompt`` keys.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        items = self._normalise_prompts(prompts)
        results: Dict[str, BatchResult] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            future_to_id = {
                pool.submit(self._run_single, item["prompt"], system_prompt): item["custom_id"]
                for item in items
            }
            for future in as_completed(future_to_id):
                cid = future_to_id[future]
                try:
                    content, stop_reason, usage = future.result()
                    results[cid] = BatchResult(
                        custom_id=cid,
                        result_type="succeeded",
                        content=content,
                        stop_reason=stop_reason,
                        usage=usage,
                    )
                except Exception as exc:  # noqa: BLE001
                    log_warning(f"BatchRunner: request {cid!r} failed: {exc}")
                    results[cid] = BatchResult(
                        custom_id=cid,
                        result_type="errored",
                        error=str(exc),
                    )

        return [results[item["custom_id"]] for item in items]

    async def arun_batch(
        self,
        prompts: List[Union[str, Dict[str, Any]]],
        system_prompt: Optional[str] = None,
    ) -> List[BatchResult]:
        """Async version of :meth:`run_batch`."""
        import asyncio

        items = self._normalise_prompts(prompts)

        async def _run(item: Dict[str, Any]) -> BatchResult:
            try:
                content, stop_reason, usage = await self._arun_single(
                    item["prompt"], system_prompt
                )
                return BatchResult(
                    custom_id=item["custom_id"],
                    result_type="succeeded",
                    content=content,
                    stop_reason=stop_reason,
                    usage=usage,
                )
            except Exception as exc:  # noqa: BLE001
                return BatchResult(
                    custom_id=item["custom_id"],
                    result_type="errored",
                    error=str(exc),
                )

        return list(await asyncio.gather(*[_run(item) for item in items]))

    def _run_single(
        self, prompt: str, system_prompt: Optional[str]
    ) -> tuple:
        from buddy.models.message import Message

        messages = [Message(role="user", content=prompt)]
        if system_prompt:
            messages.insert(0, Message(role="system", content=system_prompt))
        resp = self.model.invoke(messages=messages)
        content = getattr(resp, "content", str(resp))
        stop_reason = getattr(resp, "stop_reason", None)
        usage = None
        if hasattr(resp, "usage"):
            usage = {
                "input_tokens": getattr(resp.usage, "input_tokens", 0),
                "output_tokens": getattr(resp.usage, "output_tokens", 0),
            }
        return content, stop_reason, usage

    async def _arun_single(
        self, prompt: str, system_prompt: Optional[str]
    ) -> tuple:
        from buddy.models.message import Message

        messages = [Message(role="user", content=prompt)]
        if system_prompt:
            messages.insert(0, Message(role="system", content=system_prompt))
        resp = await self.model.ainvoke(messages=messages)
        content = getattr(resp, "content", str(resp))
        stop_reason = getattr(resp, "stop_reason", None)
        usage = None
        if hasattr(resp, "usage"):
            usage = {
                "input_tokens": getattr(resp.usage, "input_tokens", 0),
                "output_tokens": getattr(resp.usage, "output_tokens", 0),
            }
        return content, stop_reason, usage

    @staticmethod
    def _normalise_prompts(
        prompts: List[Union[str, Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        result = []
        for i, p in enumerate(prompts):
            if isinstance(p, str):
                result.append({"custom_id": f"req-{i}", "prompt": p})
            else:
                result.append({
                    "custom_id": p.get("custom_id", f"req-{i}"),
                    "prompt": p.get("prompt", p.get("content", str(p))),
                })
        return result
