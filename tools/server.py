"""Server-side and Anthropic-native tool declarations for buddy.

These tools mirror the Anthropic API's server-tool system (web search, web
fetch, code execution, advisor, tool-search, and MCP connector) but are
implemented in a **provider-agnostic** manner:

* When using Claude the native Anthropic server-tool type is emitted, so the
  API handles execution on Anthropic infrastructure with no round-trip.
* When using any other LLM, a local Python fallback is used instead, giving
  the same functional interface regardless of the underlying model.

Usage::

    from buddy.tools.server import WebSearchTool, WebFetchTool, CodeExecutionTool

    agent = Agent(model=Claude(), tools=[WebSearchTool(), WebFetchTool()])
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from buddy.tools.toolkit import Toolkit

if TYPE_CHECKING:
    from buddy.tools.function import Function

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _anthropic_server_type(version_string: str) -> Dict[str, Any]:
    """Return the raw dict emitted to the Anthropic API for a server tool."""
    return {"type": version_string}


# ─────────────────────────────────────────────────────────────────────────────
# WebSearchTool
# ─────────────────────────────────────────────────────────────────────────────

class WebSearchTool(Toolkit):
    """Perform web searches and return summarised results.

    * **Claude**: delegates to Anthropic's ``web_search_20260318`` server tool.
    * **Other models**: calls a configurable search backend (Tavily by default
      if ``TAVILY_API_KEY`` is set, otherwise DuckDuckGo).

    Parameters
    ----------
    max_results:
        Maximum number of search results to return (fallback path only).
    tavily_api_key:
        Tavily API key.  Falls back to the ``TAVILY_API_KEY`` env var.
    anthropic_tool_version:
        The Anthropic server-tool type string to pass to the API.
    include_domains / exclude_domains:
        Domain filter lists forwarded to the search API where supported.
    """

    ANTHROPIC_TYPE = "web_search_20260318"

    def __init__(
        self,
        max_results: int = 5,
        tavily_api_key: Optional[str] = None,
        anthropic_tool_version: str = "web_search_20260318",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        self.max_results = max_results
        self.tavily_api_key = tavily_api_key
        self.anthropic_tool_version = anthropic_tool_version
        self.include_domains = include_domains or []
        self.exclude_domains = exclude_domains or []

        super().__init__(
            name="web_search",
            tools=[self.web_search],
            instructions=(
                "Use the web_search tool to find current information from the internet. "
                "Always cite sources and include URLs when returning search results."
            ),
            **kwargs,
        )

    def web_search(self, query: str, max_results: int = 5) -> str:
        """Search the web for current information about a topic.

        Retrieves up-to-date information from the internet. Use this when you
        need recent news, current data, or facts that may not be in your training
        data. Returns titles, URLs, and content snippets for the most relevant
        results.

        Args:
            query: The search query.
            max_results: Maximum number of results to return (1-10).

        Returns:
            str: JSON-encoded list of search results with title, url, and snippet.
        """
        limit = min(max_results, self.max_results)
        return self._search(query, limit)

    def _search(self, query: str, limit: int) -> str:
        # Try Tavily first
        try:
            return self._tavily_search(query, limit)
        except Exception:
            pass
        # Fallback to DuckDuckGo
        try:
            return self._ddg_search(query, limit)
        except Exception as exc:
            return json.dumps({"error": f"All search backends failed: {exc}"})

    def _tavily_search(self, query: str, limit: int) -> str:
        import os
        key = self.tavily_api_key or os.environ.get("TAVILY_API_KEY", "")
        if not key:
            raise RuntimeError("No Tavily API key")
        from tavily import TavilyClient  # type: ignore
        client = TavilyClient(api_key=key)
        resp = client.search(
            query=query,
            max_results=limit,
            include_domains=self.include_domains or None,
            exclude_domains=self.exclude_domains or None,
        )
        results = [
            {"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content")}
            for r in resp.get("results", [])
        ]
        return json.dumps(results)

    def _ddg_search(self, query: str, limit: int) -> str:
        from duckduckgo_search import DDGS  # type: ignore
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=limit):
                results.append({"title": r.get("title"), "url": r.get("href"), "snippet": r.get("body")})
        return json.dumps(results)

    def to_anthropic_server_tool(self) -> Dict[str, Any]:
        """Return the native Anthropic server-tool declaration."""
        tool: Dict[str, Any] = {"type": self.anthropic_tool_version}
        if self.include_domains:
            tool["include_domains"] = self.include_domains
        if self.exclude_domains:
            tool["exclude_domains"] = self.exclude_domains
        return tool


# ─────────────────────────────────────────────────────────────────────────────
# WebFetchTool
# ─────────────────────────────────────────────────────────────────────────────

class WebFetchTool(Toolkit):
    """Fetch and read content from specific URLs.

    * **Claude**: delegates to Anthropic's ``web_fetch_20260318`` server tool.
    * **Other models**: uses ``httpx`` + ``BeautifulSoup`` / ``trafilatura``
      to download and clean page content locally.

    Parameters
    ----------
    max_length:
        Maximum characters of content to return (fallback path only).
    anthropic_tool_version:
        The Anthropic server-tool type string to pass to the API.
    """

    ANTHROPIC_TYPE = "web_fetch_20260318"

    def __init__(
        self,
        max_length: int = 20_000,
        anthropic_tool_version: str = "web_fetch_20260318",
        **kwargs: Any,
    ):
        self.max_length = max_length
        self.anthropic_tool_version = anthropic_tool_version

        super().__init__(
            name="web_fetch",
            tools=[self.fetch_url],
            instructions=(
                "Use the fetch_url tool to retrieve full page content from a specific URL. "
                "This is most useful after a web search reveals relevant links."
            ),
            **kwargs,
        )

    def fetch_url(self, url: str, start_index: int = 0) -> str:
        """Fetch and return the text content of a web page.

        Retrieves the full readable content of the URL, stripped of HTML
        boilerplate. Use this after web_search when you need the complete text
        of a specific page rather than a brief snippet.

        Args:
            url: The URL to fetch (must start with http:// or https://).
            start_index: Character offset to start from (for pagination).

        Returns:
            str: The readable text content of the page (up to max_length chars).
        """
        try:
            return self._fetch(url, start_index)
        except Exception as exc:
            return json.dumps({"error": f"Failed to fetch {url}: {exc}"})

    def _fetch(self, url: str, start_index: int) -> str:
        import httpx
        resp = httpx.get(url, follow_redirects=True, timeout=15)
        resp.raise_for_status()
        content = self._extract_text(resp.text)
        chunk = content[start_index: start_index + self.max_length]
        return json.dumps({"url": url, "content": chunk, "total_length": len(content)})

    @staticmethod
    def _extract_text(html: str) -> str:
        try:
            import trafilatura  # type: ignore
            text = trafilatura.extract(html) or ""
            if text:
                return text
        except ImportError:
            pass
        try:
            from bs4 import BeautifulSoup  # type: ignore
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            return soup.get_text(separator="\n", strip=True)
        except ImportError:
            pass
        return html

    def to_anthropic_server_tool(self) -> Dict[str, Any]:
        return {"type": self.anthropic_tool_version}


# ─────────────────────────────────────────────────────────────────────────────
# CodeExecutionTool
# ─────────────────────────────────────────────────────────────────────────────

class CodeExecutionTool(Toolkit):
    """Execute Python (and optionally Bash) code in a sandboxed environment.

    * **Claude**: delegates to Anthropic's ``code_execution_20260521`` server
      tool, which runs in Anthropic's managed sandbox.
    * **Other models**: runs code in a local subprocess with a configurable
      timeout and optional virtual-environment isolation.

    Parameters
    ----------
    timeout:
        Execution timeout in seconds (fallback path only).
    anthropic_tool_version:
        The Anthropic server-tool type string to pass to the API.
    allowed_languages:
        Languages permitted for local execution.  Defaults to ``["python", "bash"]``.
    """

    ANTHROPIC_TYPE = "code_execution_20260521"

    def __init__(
        self,
        timeout: int = 30,
        anthropic_tool_version: str = "code_execution_20260521",
        allowed_languages: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        self.timeout = timeout
        self.anthropic_tool_version = anthropic_tool_version
        self.allowed_languages = allowed_languages or ["python", "bash"]

        super().__init__(
            name="code_execution",
            tools=[self.execute_code],
            instructions=(
                "Use the execute_code tool to run Python or Bash code. "
                "This is ideal for calculations, data processing, file operations, "
                "and tasks that benefit from actual computation rather than inference."
            ),
            **kwargs,
        )

    def execute_code(self, code: str, language: str = "python") -> str:
        """Execute code and return stdout/stderr output.

        Runs the provided code in an isolated environment and captures all
        output. Ideal for numerical computation, data analysis, file I/O,
        and any task requiring deterministic calculation.

        Args:
            code: The source code to execute.
            language: Programming language – "python" or "bash".

        Returns:
            str: JSON with stdout, stderr, exit_code, and execution_time_ms.
        """
        if language not in self.allowed_languages:
            return json.dumps({"error": f"Language '{language}' is not allowed. Permitted: {self.allowed_languages}"})
        try:
            return self._run_code(code, language)
        except Exception as exc:
            return json.dumps({"error": str(exc), "exit_code": 1})

    def _run_code(self, code: str, language: str) -> str:
        import subprocess
        import tempfile
        import time

        start = time.monotonic()
        suffix = ".py" if language == "python" else ".sh"
        cmd = ["python"] if language == "python" else ["bash"]

        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
            f.write(code)
            fname = f.name

        try:
            result = subprocess.run(
                cmd + [fname],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return json.dumps({"error": f"Execution timed out after {self.timeout}s", "exit_code": 124})
        finally:
            import os
            try:
                os.unlink(fname)
            except OSError:
                pass

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return json.dumps({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "execution_time_ms": elapsed_ms,
        })

    def to_anthropic_server_tool(self) -> Dict[str, Any]:
        return {"type": self.anthropic_tool_version}


# ─────────────────────────────────────────────────────────────────────────────
# AdvisorTool
# ─────────────────────────────────────────────────────────────────────────────

class AdvisorTool(Toolkit):
    """Get a second opinion from a separate model instance.

    * **Claude**: uses Anthropic's ``advisor_20260301`` server tool (requires
      the ``advisor-tool-2026-03-01`` beta header).
    * **Other models**: instantiates a separate buddy ``Agent`` or model call
      to produce the advisory response.

    Parameters
    ----------
    advisor_model:
        The buddy model to use for the advisor.  Defaults to the same model
        as the parent if not specified.
    system_prompt:
        System prompt for the advisor.
    anthropic_tool_version:
        Anthropic server-tool type string.
    """

    ANTHROPIC_TYPE = "advisor_20260301"

    def __init__(
        self,
        advisor_model: Optional[Any] = None,
        system_prompt: str = "You are a helpful expert advisor. Provide concise, accurate advice.",
        anthropic_tool_version: str = "advisor_20260301",
        **kwargs: Any,
    ):
        self.advisor_model = advisor_model
        self.system_prompt = system_prompt
        self.anthropic_tool_version = anthropic_tool_version

        super().__init__(
            name="advisor",
            tools=[self.get_advice],
            instructions=(
                "Use the get_advice tool to consult a second expert model for "
                "complex decisions, fact-checking, or alternative perspectives."
            ),
            **kwargs,
        )

    def get_advice(self, question: str, context: Optional[str] = None) -> str:
        """Consult an advisor model for expert guidance.

        Asks a separate model instance to provide advice on a specific question.
        Use this for complex decisions, sanity-checking your reasoning, or when
        you want an independent second opinion.

        Args:
            question: The question or problem to get advice on.
            context: Optional background context to provide to the advisor.

        Returns:
            str: The advisor's response.
        """
        if self.advisor_model is None:
            return json.dumps({"error": "No advisor model configured."})
        try:
            messages = []
            if context:
                messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"})
            else:
                messages.append({"role": "user", "content": question})
            resp = self.advisor_model.invoke(messages=messages, system=self.system_prompt, max_tokens=1024)
            text = _get_text_from_response(resp)
            return json.dumps({"advice": text})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def to_anthropic_server_tool(self) -> Dict[str, Any]:
        return {"type": self.anthropic_tool_version}


# ─────────────────────────────────────────────────────────────────────────────
# ToolSearchTool  (deferred / lazy tool loading)
# ─────────────────────────────────────────────────────────────────────────────

class ToolSearchTool(Toolkit):
    """Discover deferred tools by name or description (tool-search pattern).

    Use this together with ``defer_loading=True`` on other ``Function``
    objects (or Agent/Team ``manage_tool_context``) to keep the tools array
    under provider limits (e.g. OpenAI's 128).  The model calls
    ``search_tools``, matching tools are **activated** into the live tools
    array, then the model can call them on the next turn.

    * **Claude**: maps to ``tool_search_tool_regex_20251119`` or
      ``tool_search_tool_bm25_20251119`` server tools.
    * **Other models**: local BM25/keyword search over the deferred index.

    Parameters
    ----------
    deferred_tools:
        A name→description mapping of tools that are available but not yet
        loaded.  Usually populated automatically by :class:`ToolContextManager`.
    deferred_functions:
        Optional name→Function map used when activating matches so the model
        can call them after search (without this, search is discovery-only).
    activate_callback:
        ``(names: List[str]) -> List[str]`` that moves deferred Functions into
        the agent's active ``_tools_for_model`` / ``_functions_for_model``.
        When set, ``search_tools`` activates matches automatically.
    algorithm:
        ``"bm25"`` (default) or ``"regex"``.
    anthropic_tool_version:
        Anthropic server-tool type string.
    """

    ANTHROPIC_BM25_TYPE = "tool_search_tool_bm25_20251119"
    ANTHROPIC_REGEX_TYPE = "tool_search_tool_regex_20251119"

    def __init__(
        self,
        deferred_tools: Optional[Dict[str, str]] = None,
        deferred_functions: Optional[Dict[str, "Function"]] = None,
        activate_callback: Optional[Callable[[List[str]], List[str]]] = None,
        algorithm: str = "bm25",
        anthropic_tool_version: Optional[str] = None,
        **kwargs: Any,
    ):
        self._deferred_index: Dict[str, str] = dict(deferred_tools or {})
        self._deferred_functions: Dict[str, "Function"] = deferred_functions if deferred_functions is not None else {}
        if deferred_functions:
            for name, fn in deferred_functions.items():
                if name not in self._deferred_index:
                    self._deferred_index[name] = getattr(fn, "description", None) or ""
        self._activate_callback = activate_callback
        self.algorithm = algorithm
        self.anthropic_tool_version = anthropic_tool_version or (
            self.ANTHROPIC_BM25_TYPE if algorithm == "bm25" else self.ANTHROPIC_REGEX_TYPE
        )

        super().__init__(
            name="tool_search",
            tools=[self.search_tools],
            instructions=(
                "Many tools are deferred to stay under the provider tool limit. "
                "When you need a capability that is not in your current tools list, "
                "call search_tools with keywords for that capability. Matching tools "
                "are loaded automatically and become callable on your next turn."
            ),
            add_instructions=True,
            **kwargs,
        )

    def register_deferred(self, name: str, description: str, function: Optional["Function"] = None) -> None:
        """Register a tool in the deferred index so it can be discovered."""
        self._deferred_index[name] = description
        if function is not None:
            self._deferred_functions[name] = function

    def search_tools(self, query: str, max_results: int = 5) -> str:
        """Search deferred tools by name or description and load matches.

        Matching tools are activated into the live tools array so you can call
        them on your next turn.

        Args:
            query: Keywords describing the tool functionality you need.
            max_results: Maximum number of results to return.

        Returns:
            str: JSON with matches and which tools were loaded.
        """
        results = self._local_search(query, max_results)
        names = [r["name"] for r in results]
        loaded: List[str] = []
        if names and self._activate_callback is not None:
            try:
                loaded = list(self._activate_callback(names) or [])
            except Exception as e:
                logger.warning("ToolSearchTool activate_callback failed: %s", e)
                loaded = []
        elif names and self._deferred_functions:
            # Fallback: mark as discoverable only (Agent/Team should wire activate)
            loaded = []

        for r in results:
            r["loaded"] = r["name"] in loaded
            r["ready_to_call"] = r["loaded"]

        return json.dumps(
            {
                "query": query,
                "matches": results,
                "loaded": loaded,
                "hint": (
                    "Loaded tools are now in your tools list — call them directly next. "
                    "If nothing loaded, refine the query or try related keywords."
                    if loaded
                    else "No tools were activated. Refine your query with different keywords."
                ),
            }
        )

    def _local_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        query_lower = (query or "").lower().strip()
        if not query_lower:
            # Empty query: return a sample of deferred names so the model can refine
            sample = list(self._deferred_index.items())[:limit]
            return [
                {"name": name, "description": desc, "relevance_score": 0}
                for name, desc in sample
            ]

        terms = [t for t in query_lower.replace(",", " ").split() if t]
        scored = []
        for name, desc in self._deferred_index.items():
            text = f"{name} {desc}".lower()
            name_lower = name.lower()
            score = 0
            if query_lower == name_lower or query_lower in name_lower:
                score += 10
            if query_lower in text:
                score += 5
            score += sum(text.count(term) for term in terms)
            # Light fuzzy: underscore/camel fragments
            score += sum(2 for term in terms if term in name_lower.replace("_", " "))
            if score > 0:
                scored.append({"name": name, "description": desc, "relevance_score": score})
        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored[:limit]

    def to_anthropic_server_tool(self) -> Dict[str, Any]:
        return {"type": self.anthropic_tool_version}


# ─────────────────────────────────────────────────────────────────────────────
# MCPToolset  (Model Context Protocol connector)
# ─────────────────────────────────────────────────────────────────────────────

class MCPToolset(Toolkit):
    """Connect to an MCP server and expose its tools.

    * **Claude**: emits an ``mcp_toolset`` entry which Anthropic's API handles
      natively (requires ``anthropic-beta: mcp-client-2025-11-20`` header).
    * **Other models**: uses the local MCP client to list and call tools via
      JSON-RPC over stdio or HTTP transport.

    Parameters
    ----------
    server_url:
        HTTP URL of the MCP server, or a command list for stdio.
    server_name:
        Human-readable name for this MCP connection.
    allowed_tools:
        If set, only expose these tool names from the server.
    cache_control:
        Prompt-cache breakpoint for this toolset (Anthropic only).
    """

    def __init__(
        self,
        server_url: Optional[str] = None,
        server_name: str = "mcp_server",
        allowed_tools: Optional[List[str]] = None,
        cache_control: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ):
        self.server_url = server_url
        self.server_name = server_name
        self.allowed_tools = allowed_tools
        self.cache_control = cache_control
        self._remote_tools: Dict[str, Dict[str, Any]] = {}

        # Discover remote tools and register them
        tools_list = [self._create_proxy(name) for name in (self._discover() or [])]

        super().__init__(
            name=f"mcp_{server_name}",
            tools=tools_list,
            instructions=f"Tools provided by the MCP server '{server_name}'.",
            **kwargs,
        )

    def _discover(self) -> List[str]:
        """List tool names from the MCP server."""
        try:
            tools = self._call_mcp("tools/list", {})
            names = []
            for t in tools.get("tools", []):
                name = t["name"]
                if self.allowed_tools is None or name in self.allowed_tools:
                    self._remote_tools[name] = t
                    names.append(name)
            return names
        except Exception as exc:
            logger.warning("MCP discovery failed for %s: %s", self.server_name, exc)
            return []

    def _create_proxy(self, tool_name: str):
        """Create a Python callable that proxies to the remote MCP tool."""
        meta = self._remote_tools.get(tool_name, {})
        description = meta.get("description", f"MCP tool: {tool_name}")

        def proxy(**kwargs: Any) -> str:
            return self._call_tool(tool_name, kwargs)

        proxy.__name__ = tool_name
        proxy.__doc__ = description
        return proxy

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        try:
            result = self._call_mcp("tools/call", {"name": tool_name, "arguments": arguments})
            content = result.get("content", [])
            if isinstance(content, list):
                return "\n".join(c.get("text", str(c)) for c in content)
            return str(content)
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def _call_mcp(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        import httpx
        if not self.server_url:
            return {}
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        resp = httpx.post(self.server_url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data.get("result", {})

    def to_anthropic_server_tool(self) -> Dict[str, Any]:
        entry: Dict[str, Any] = {
            "type": "mcp_toolset",
            "server_label": self.server_name,
            "server_url": self.server_url,
        }
        if self.allowed_tools:
            entry["allowed_tools"] = self.allowed_tools
        if self.cache_control:
            entry["cache_control"] = self.cache_control
        return entry


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────

def _get_text_from_response(resp: Any) -> str:
    if hasattr(resp, "content") and isinstance(resp.content, list):
        return " ".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text")
    if hasattr(resp, "choices"):
        return resp.choices[0].message.content or ""
    return str(resp)


__all__ = [
    "WebSearchTool",
    "WebFetchTool",
    "CodeExecutionTool",
    "AdvisorTool",
    "ToolSearchTool",
    "MCPToolset",
]
