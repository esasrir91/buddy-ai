"""Pre-built tool combinations for common agent patterns.

Mirrors the Anthropic "Tool combinations" guide.  Each combination returns a
list of buddy toolkits ready to pass to an ``Agent`` or ``ToolRunner``.

All combinations work with **any LLM** – not just Claude.

Available combinations
----------------------
* :func:`research_agent_tools`      – web_search + code_execution
* :func:`coding_agent_tools`        – text_editor + bash
* :func:`cite_fetch_tools`          – web_search + web_fetch
* :func:`long_running_agent_tools`  – memory + any extra tools
* :func:`browser_agent_tools`       – browser_use (Playwright/Selenium)
* :func:`full_suite_tools`          – all of the above

Usage::

    from buddy.tools.combinations import research_agent_tools

    agent = Agent(model=Claude(), tools=research_agent_tools())
    agent.run("Compare this quarter's earnings across the top 5 cloud providers.")
"""

from __future__ import annotations

from typing import Any, List, Optional

from buddy.tools.toolkit import Toolkit


# ─────────────────────────────────────────────────────────────────────────────
# Research agent: web_search + code_execution
# ─────────────────────────────────────────────────────────────────────────────

def research_agent_tools(
    tavily_api_key: Optional[str] = None,
    max_search_results: int = 5,
    code_timeout: int = 30,
    **kwargs: Any,
) -> List[Toolkit]:
    """Research agent toolkit: web search + code execution.

    The model searches the web for data, then writes and runs Python to
    process, tabulate, or visualise it.  Ideal for questions that need both
    current information and non-trivial computation.

    Parameters
    ----------
    tavily_api_key:
        Tavily API key (falls back to TAVILY_API_KEY env var, then DuckDuckGo).
    max_search_results:
        Maximum results per web search call.
    code_timeout:
        Code execution timeout in seconds.

    Returns
    -------
    List[Toolkit]
        ``[WebSearchTool, CodeExecutionTool]``

    Example::

        agent = Agent(model=..., tools=research_agent_tools())
        agent.run("Compare cloud provider pricing trends for 2026.")
    """
    from buddy.tools.server import CodeExecutionTool, WebSearchTool

    return [
        WebSearchTool(
            max_results=max_search_results,
            tavily_api_key=tavily_api_key,
            **{k: v for k, v in kwargs.items() if k in ("include_domains", "exclude_domains")},
        ),
        CodeExecutionTool(timeout=code_timeout),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Coding agent: text_editor + bash
# ─────────────────────────────────────────────────────────────────────────────

def coding_agent_tools(
    base_dir: Optional[str] = None,
    bash_timeout: int = 120,
    max_view_lines: int = 500,
    allowed_commands: Optional[List[str]] = None,
    **kwargs: Any,
) -> List[Toolkit]:
    """Coding agent toolkit: text editor + bash shell.

    The canonical software-development loop – inspect the code, make an edit,
    run the tests, repeat.  Both tools are executed locally by the agent
    framework.

    Parameters
    ----------
    base_dir:
        Root directory for file operations.  Defaults to the current directory.
    bash_timeout:
        Maximum seconds per shell command.
    max_view_lines:
        Maximum lines returned by the text editor's view operation.
    allowed_commands:
        Optional allowlist of shell command prefixes for the bash tool.

    Returns
    -------
    List[Toolkit]
        ``[TextEditorTool, BashTool]``

    Example::

        agent = Agent(model=..., tools=coding_agent_tools(base_dir="/workspace"))
        agent.run("Fix the failing unit test in tests/test_api.py")
    """
    from buddy.tools.bash_tool import BashTool
    from buddy.tools.text_editor import TextEditorTool

    return [
        TextEditorTool(base_dir=base_dir, max_view_lines=max_view_lines),
        BashTool(
            working_directory=base_dir,
            timeout=bash_timeout,
            allowed_commands=allowed_commands,
        ),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Cite-then-fetch: web_search + web_fetch
# ─────────────────────────────────────────────────────────────────────────────

def cite_fetch_tools(
    tavily_api_key: Optional[str] = None,
    max_search_results: int = 5,
    max_fetch_length: int = 20_000,
    **kwargs: Any,
) -> List[Toolkit]:
    """Cite-then-fetch toolkit: web search + web fetch.

    The model first searches to surface candidate URLs, inspects the snippets,
    picks the relevant ones, then fetches their full content.  Ideal when the
    answer is in long-form articles, documentation, or specs.

    Parameters
    ----------
    tavily_api_key:
        Tavily API key.
    max_search_results:
        Maximum results per search.
    max_fetch_length:
        Maximum characters of page content returned per fetch.

    Returns
    -------
    List[Toolkit]
        ``[WebSearchTool, WebFetchTool]``

    Example::

        agent = Agent(model=..., tools=cite_fetch_tools())
        agent.run("Summarise the RFC for HTTP/3 with exact quotes.")
    """
    from buddy.tools.server import WebFetchTool, WebSearchTool

    return [
        WebSearchTool(max_results=max_search_results, tavily_api_key=tavily_api_key),
        WebFetchTool(max_length=max_fetch_length),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Long-running agent: memory + any other tools
# ─────────────────────────────────────────────────────────────────────────────

def long_running_agent_tools(
    extra_tools: Optional[List[Toolkit]] = None,
    db_path: Optional[str] = None,
    namespace: str = "default",
    max_memories: int = 1000,
    **kwargs: Any,
) -> List[Toolkit]:
    """Long-running agent toolkit: memory + any other tools.

    Memory persists facts across conversations so the agent can remember
    prior sessions, user preferences, and decisions made in the past.  Add
    any other tools alongside memory to create a persistent specialist agent.

    Parameters
    ----------
    extra_tools:
        Additional toolkits to include alongside memory.
    db_path:
        Path to the SQLite database for memory storage.
    namespace:
        Namespace to isolate memories per agent or user.
    max_memories:
        Maximum number of memory entries to store.

    Returns
    -------
    List[Toolkit]
        ``[MemoryTool, *extra_tools]``

    Example::

        agent = Agent(
            model=...,
            tools=long_running_agent_tools(extra_tools=coding_agent_tools()),
        )
    """
    from buddy.tools.memory_tool import MemoryTool

    tools: List[Toolkit] = [
        MemoryTool(db_path=db_path, namespace=namespace, max_memories=max_memories)
    ]
    if extra_tools:
        tools.extend(extra_tools)
    return tools


# ─────────────────────────────────────────────────────────────────────────────
# Browser agent: browser_use
# ─────────────────────────────────────────────────────────────────────────────

def browser_agent_tools(
    headless: bool = True,
    browser: str = "chromium",
    timeout: int = 30_000,
    allowed_domains: Optional[List[str]] = None,
    **kwargs: Any,
) -> List[Toolkit]:
    """Browser agent toolkit: full browser automation.

    When the entire task happens inside web pages (filling forms, reading
    content, navigating multi-page flows), the browser tool is a closer fit
    than computer use.

    Parameters
    ----------
    headless:
        Run without a visible browser window.
    browser:
        Browser engine: ``"chromium"`` (default), ``"firefox"``, or ``"webkit"``.
    timeout:
        Default action timeout in milliseconds.
    allowed_domains:
        Optional domain allowlist to restrict navigation.

    Returns
    -------
    List[Toolkit]
        ``[BrowserUseToolset]``

    Example::

        agent = Agent(model=..., tools=browser_agent_tools(headless=False))
        agent.run("Fill out the contact form at https://example.com/contact")
    """
    from buddy.tools.browser import BrowserUseToolset

    return [
        BrowserUseToolset(
            headless=headless,
            browser=browser,
            timeout=timeout,
            allowed_domains=allowed_domains,
        )
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Computer-use agent: desktop automation
# ─────────────────────────────────────────────────────────────────────────────

def computer_use_tools(
    screenshot_quality: int = 75,
    scale_factor: float = 1.0,
    enable_clipboard: bool = True,
    **kwargs: Any,
) -> List[Toolkit]:
    """Computer-use agent toolkit: full desktop automation.

    Use this when the task requires arbitrary GUI interaction across desktop
    applications.  The model sees screenshots and issues mouse/keyboard actions.

    Parameters
    ----------
    screenshot_quality:
        JPEG/PNG quality for screenshots (reduces token cost at lower values).
    scale_factor:
        Scale screenshots before sending (e.g. 0.5 halves resolution).
    enable_clipboard:
        If ``True``, expose clipboard read/write tools.

    Returns
    -------
    List[Toolkit]
        ``[ComputerUseToolset]``

    Example::

        agent = Agent(model=..., tools=computer_use_tools())
        agent.run("Open the calculator application and compute 123 * 456.")
    """
    from buddy.tools.computer import ComputerUseToolset

    return [
        ComputerUseToolset(
            screenshot_quality=screenshot_quality,
            scale_factor=scale_factor,
            enable_clipboard=enable_clipboard,
        )
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Full suite
# ─────────────────────────────────────────────────────────────────────────────

def full_suite_tools(
    base_dir: Optional[str] = None,
    db_path: Optional[str] = None,
    tavily_api_key: Optional[str] = None,
    headless: bool = True,
    **kwargs: Any,
) -> List[Toolkit]:
    """All standard tools bundled together.

    Combines research, coding, web-fetch, memory, and browser tools in a
    single list.  Use this as a starting point for general-purpose agents
    and remove the tools you don't need.

    Returns
    -------
    List[Toolkit]
        All tool combinations.
    """
    return [
        *research_agent_tools(tavily_api_key=tavily_api_key),
        *coding_agent_tools(base_dir=base_dir),
        *cite_fetch_tools(tavily_api_key=tavily_api_key),
        *long_running_agent_tools(db_path=db_path),
        *browser_agent_tools(headless=headless),
    ]


__all__ = [
    "research_agent_tools",
    "coding_agent_tools",
    "cite_fetch_tools",
    "long_running_agent_tools",
    "browser_agent_tools",
    "computer_use_tools",
    "full_suite_tools",
]
