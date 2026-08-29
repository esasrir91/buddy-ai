from buddy.tools.decorator import tool
from buddy.tools.function import Function, FunctionCall
from buddy.tools.token_manager import TokenManager
from buddy.tools.toolkit import Toolkit

# ── New tool-use infrastructure ───────────────────────────────────────────────
from buddy.tools.runner import ToolRunner, RunnerMessage, tool_runner

# Client tools (executed locally, work with any LLM)
from buddy.tools.bash_tool import BashTool
from buddy.tools.text_editor import TextEditorTool
from buddy.tools.memory_tool import MemoryTool
from buddy.tools.computer import ComputerUseToolset
from buddy.tools.browser import BrowserUseToolset

# Server / server-proxied tools
from buddy.tools.server import (
    WebSearchTool,
    WebFetchTool,
    CodeExecutionTool,
    AdvisorTool,
    ToolSearchTool,
    MCPToolset,
)

# Context management
from buddy.tools.context_manager import (
    ToolContextManager,
    activate_deferred_tools,
    inject_tool_search,
    move_overflow_to_deferred,
    should_manage_tool_context,
)

# Pre-built combinations
from buddy.tools.combinations import (
    research_agent_tools,
    coding_agent_tools,
    cite_fetch_tools,
    long_running_agent_tools,
    browser_agent_tools,
    computer_use_tools,
    full_suite_tools,
    cursor_agent_tools,
)

# CursorTools – Cursor-parity toolkit for Aura
from buddy.tools.cursor import CursorTools

__all__ = [
    # Core
    "tool",
    "Function",
    "FunctionCall",
    "Toolkit",
    "TokenManager",
    # Tool runner
    "ToolRunner",
    "RunnerMessage",
    "tool_runner",
    # Client tools
    "BashTool",
    "TextEditorTool",
    "MemoryTool",
    "ComputerUseToolset",
    "BrowserUseToolset",
    # Server tools
    "WebSearchTool",
    "WebFetchTool",
    "CodeExecutionTool",
    "AdvisorTool",
    "ToolSearchTool",
    "MCPToolset",
    # Context management
    "ToolContextManager",
    "activate_deferred_tools",
    "inject_tool_search",
    "move_overflow_to_deferred",
    "should_manage_tool_context",
    # Combinations
    "research_agent_tools",
    "coding_agent_tools",
    "cite_fetch_tools",
    "long_running_agent_tools",
    "browser_agent_tools",
    "computer_use_tools",
    "full_suite_tools",
    "cursor_agent_tools",
    # CursorTools
    "CursorTools",
]
