#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test.py  --  Buddy Autonomous Power Agent
==========================================
A fully autonomous, self-configuring AI agent + team system.
Every capability is driven exclusively through the buddy framework.

FULLY AUTONOMOUS — zero interactive prompts required:
  ✦ Boots straight into AUTO mode (override: --model=<id> or BUDDY_MODEL env)
  ✦ Every task is re-routed: model, effort, thinking, team, advisor & RAG
    are switched autonomously by the meta-agent (runner reused when unchanged)
  ✦ Agentic RAG — local iRAG KB over workspace docs (buddy_knowledge.db);
    agent decides when to search (search_knowledge) and autonomously saves
    new learnings back (update_knowledge); ingestion runs in background
  ✦ Self-healing — failed runs auto-escalate effort (low→medium→high→xhigh→max)
    and rebuild the runner with the session preserved (up to 2 retries)
  ✦ First-class model configs (buddy.models): EffortConfig (native per
    provider + prompt-hint fallback), ThinkingConfig (validated adaptive),
    PromptCacheConfig (system+tools+history breakpoints), FastModeConfig
    (auto fast speed for low/medium-effort Opus tasks, 429 fallback),
    MultilingualConfig (meta-agent detects user language -> native replies),
    refusal_fallback_model (auto-retry on sibling Claude)
  ✦ Autonomous tool selection (auto_tool_selection) + prompt caching
  ✦ Monitoring — every run logged to buddy_metrics.db (latency, tokens, tool
    calls/errors, escalations); reliability auto-checked per run; /metrics
  ✦ Live competency (buddy.eval CompetencyTracker) — per-domain EMA scores
    from real outcomes, persisted; weak domains get autonomous effort boosts
  ✦ Evals on demand — /eval <expected> (LLM-as-judge accuracy on last answer),
    /eval reliability <tools> (tool-call verification); results feed competency
  ✦ Headless operation: CLI args or piped stdin; TTY loop only as fallback
  ✦ /switch, /advisor, /rag are argument-driven (no menus); --debug for logs

Dynamic / auto capabilities (all via buddy):
  ✦ Model selection   — AUTO default: meta-agent picks optimal model per task
  ✦ Effort control    — reasoning_effort (OpenAI o/gpt-5.x) + request_params effort (Claude)
  ✦ Thinking config   — ThinkingConfig dict: adaptive / extended / disabled (Claude)
  ✦ Token budget      — TokenBudgetConfig with auto-compress
  ✦ Team formation    — autonomous specialist Team for complex multi-domain tasks
  ✦ Memory            — SqliteMemoryDb (persistent, cross-session)
  ✦ Session storage   — SqliteAgentStorage
  ✦ Full tool suite   — all available tools auto-loaded (failures silently skipped)
  ✦ Streaming         — live thinking / reasoning / tool-call display
  ✦ Retries           — exponential backoff on transient errors
  ✦ Advisor           — strategic advisor agent for complex reasoning
  ✦ Compaction        — auto conversation compaction (server/client fallback)
  ✦ Context editing   — trims old tool results and thinking blocks
  ✦ Rich context      — workspace, platform, user, model info injected
"""

from __future__ import annotations
import os, sys, json, textwrap, threading, time, sqlite3
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

# Force UTF-8 on Windows so Unicode menu characters don't crash
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# API Keys — from environment or local .env (gitignored); never hardcode secrets
# ─────────────────────────────────────────────────────────────────────────────
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.isfile(_env_path):
    with open(_env_path, encoding="utf-8") as _env_file:
        for _line in _env_file:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _, _val = _line.partition("=")
            _key, _val = _key.strip(), _val.strip().strip('"').strip("'")
            if _key and _key not in os.environ:
                os.environ[_key] = _val

# ─────────────────────────────────────────────────────────────────────────────
# Model Catalogue
# (label, provider, model_id, ctx_k, out_k, sup_effort, sup_thinking,
#  is_reasoning, tier)
#
# sup_effort   : Claude models that accept output_config.effort
# sup_thinking : Claude models that support adaptive/extended thinking dict
# is_reasoning : OpenAI o-series / gpt-5.x — use reasoning_effort, no temp
# tier         : flagship | balanced | fast | cheap
# ─────────────────────────────────────────────────────────────────────────────
# Token limits verified against official docs (OpenAI + Anthropic, Aug 2026).
# ctx_k / out_k are in thousands of tokens (e.g. 1050 = 1,050,000).
MODELS = [
    # ── OpenAI ────────────────────────────────────────────────────────────────────
    # GPT-5.6: 1,050,000 ctx / 128,000 out
    ("GPT-5.6 Sol      flagship  $4/$20  1.05M", "oai","gpt-5.6-sol",    1050,128,True, False,True, "flagship"),
    ("GPT-5.6 Terra    balanced  $2/$12  1.05M", "oai","gpt-5.6-terra",  1050,128,True, False,True, "balanced"),
    ("GPT-5.6 Luna     cheap     $0.20   1.05M", "oai","gpt-5.6-luna",   1050,128,True, False,True, "cheap"),
    # GPT-5.5 / 5.4 flagship: 1,050,000 ctx / 128,000 out
    ("GPT-5.5          pro       $5/$30  1.05M", "oai","gpt-5.5",        1050,128,True, False,True, "flagship"),
    # gpt-5.5-pro / o3-pro require the Responses API — not compatible with OpenAIChat
    ("GPT-5.4          frontier  $2.5/$15 1.05M","oai","gpt-5.4",        1050,128,True, False,True, "flagship"),
    # GPT-5.4 Mini/Nano + GPT-5: 400,000 ctx / 128,000 out
    ("GPT-5.4 Mini     fast      $0.75   400K",  "oai","gpt-5.4-mini",    400,128,True, False,True, "fast"),
    ("GPT-5.4 Nano     ultra     $0.20   400K",  "oai","gpt-5.4-nano",    400,128,True, False,True, "cheap"),
    ("GPT-5            base      $1.25   400K",  "oai","gpt-5",           400,128,True, False,True, "balanced"),
    # GPT-4.1 family: 1,047,576 ctx / 32,768 out
    ("GPT-4.1          stable    $2/$8   1M",    "oai","gpt-4.1",        1048, 32,False,False,False, "balanced"),
    ("GPT-4.1 Mini     fast      $0.40   1M",    "oai","gpt-4.1-mini",   1048, 32,False,False,False, "fast"),
    ("GPT-4.1 Nano     cheapest  $0.10   1M",    "oai","gpt-4.1-nano",   1048, 32,False,False,False, "cheap"),
    # GPT-4o family: 128,000 ctx / 16,384 out
    ("GPT-4o           vision    $2.50   128K",  "oai","gpt-4o",          128, 16,False,False,False, "balanced"),
    ("GPT-4o Mini      small     $0.15   128K",  "oai","gpt-4o-mini",     128, 16,False,False,False, "cheap"),
    # o3: 200,000 ctx / 100,000 out
    ("o3               reasoning $2/$8   200K",  "oai","o3",              200,100,True, False,True, "flagship"),
    # ── Anthropic Claude ──────────────────────────────────────────────────────────
    # Fable/Opus/Sonnet 5 + Opus 4.6–4.8 + Sonnet 4.6: 1M ctx / 128K out
    ("Claude Fable 5   TOP TIER  $10/$50 1M",   "ant","claude-fable-5",             1000,128,True, True, False,"flagship"),
    ("Claude Opus 5    agentic   $5/$25  1M",    "ant","claude-opus-5",              1000,128,True, True, False,"flagship"),
    ("Claude Sonnet 5  balanced  $2/$10  1M",    "ant","claude-sonnet-5",            1000,128,True, True, False,"balanced"),
    # Haiku 4.5 + Sonnet 4.5: 200K ctx / 64K out
    ("Claude Haiku 4.5 fastest   $1/$5  200K",   "ant","claude-haiku-4-5-20251001",   200, 64,False,True, False,"cheap"),
    ("Claude Opus 4.8  1M  effort+compact",      "ant","claude-opus-4-8",            1000,128,True, True, False,"flagship"),
    ("Claude Opus 4.7  1M  effort+compact",      "ant","claude-opus-4-7",            1000,128,True, True, False,"flagship"),
    ("Claude Opus 4.6  1M  effort+compact",      "ant","claude-opus-4-6",            1000,128,True, True, False,"flagship"),
    ("Claude Sonnet 4.6 1M effort+compact",      "ant","claude-sonnet-4-6",          1000,128,True, True, False,"balanced"),
    ("Claude Sonnet 4.5 200K",                    "ant","claude-sonnet-4-5-20250929", 200, 64,False,True, False,"balanced"),
]
MODEL_BY_ID = {m[2]: m for m in MODELS}

# Fast/cheap meta-model for auto task-analysis
_META_ID   = "gpt-4.1-mini"
_META_PROV = "oai"

# ─────────────────────────────────────────────────────────────────────────────
# Print header + model menu
# ─────────────────────────────────────────────────────────────────────────────
def _print_menu():
    W = 76
    print()
    print("=" * W)
    print("  BUDDY  —  Autonomous Power Agent")
    print("=" * W)
    print()
    print(f"  [{'0':>2}]  AUTO  (meta-agent selects best model + team per task)")
    print()
    print("  OpenAI models")
    print("  " + "─" * 70)
    for i, m in enumerate(MODELS, 1):
        if m[1] == "oai":
            tags = []
            if m[7]: tags.append("reasoning_effort")
            tag = ("  [" + ",".join(tags) + "]") if tags else ""
            print(f"  [{i:>2}]  {m[0]}{tag}")
    print()
    print("  Anthropic Claude models")
    print("  " + "─" * 70)
    for i, m in enumerate(MODELS, 1):
        if m[1] == "ant":
            tags = []
            if m[5]: tags.append("effort")
            if m[6]: tags.append("thinking")
            tag = ("  [" + ",".join(tags) + "]") if tags else ""
            print(f"  [{i:>2}]  {m[0]}{tag}")
    print()

# ─────────────────────────────────────────────────────────────────────────────
# Fully autonomous boot — ZERO interactive prompts.
#   Priority: CLI --model=<id> > env BUDDY_MODEL > AUTO (meta-agent routes
#   model, effort, thinking, team, and advisor per task).
# ─────────────────────────────────────────────────────────────────────────────
def _resolve_boot_model() -> Optional[str]:
    """Return a fixed model_id override, or None for AUTO mode."""
    # 1) CLI flag:  python test.py --model=claude-opus-5
    for arg in sys.argv[1:]:
        if arg.startswith("--model="):
            cand = arg.split("=", 1)[1].strip()
            if cand.lower() in ("auto", ""):
                return None
            if cand in MODEL_BY_ID:
                return cand
            print(f"  [Boot] Unknown model '{cand}' — falling back to AUTO.")
            return None
    # 2) Environment override:  BUDDY_MODEL=gpt-5.6-sol
    cand = os.environ.get("BUDDY_MODEL", "").strip()
    if cand and cand.lower() != "auto":
        if cand in MODEL_BY_ID:
            return cand
        print(f"  [Boot] Unknown BUDDY_MODEL '{cand}' — falling back to AUTO.")
    # 3) Default: fully autonomous routing
    return None

# Debug/monitoring passthrough (framework env flags, no code changes needed):
#   --debug CLI flag or BUDDY_DEBUG=true  -> buddy debug logs on every agent
if "--debug" in sys.argv:
    os.environ["BUDDY_DEBUG"] = "true"

_boot_model_id = _resolve_boot_model()
AUTO_MODE = _boot_model_id is None

if AUTO_MODE:
    _sel_label = "AUTO"
    _sel_prov  = _META_PROV
    _sel_id    = _META_ID
    _sel_ctx, _sel_out = 128, 16
    _sel_eff, _sel_thnk, _sel_rsn = False, False, False
    _sel_tier  = "fast"
    print("\n  [AUTO] Fully autonomous: meta-agent selects model, effort, "
          "thinking, team & advisor per task.\n")
else:
    (_sel_label, _sel_prov, _sel_id, _sel_ctx, _sel_out,
     _sel_eff, _sel_thnk, _sel_rsn, _sel_tier) = MODEL_BY_ID[_boot_model_id]
    print(f"\n  Model  : {_sel_label.strip()}  (pinned via override)")
    print(f"  ID     : {_sel_id}")
    print(f"  Ctx    : {_sel_ctx}K   Out: {_sel_out}K   Tier: {_sel_tier}")
    caps = []
    if _sel_rsn:  caps.append("reasoning_effort")
    if _sel_prov == "ant" and _sel_eff:  caps.append("effort")
    if _sel_prov == "ant" and _sel_thnk: caps.append("thinking")
    if caps: print(f"  Caps   : {', '.join(caps)}")
    print()

# ─────────────────────────────────────────────────────────────────────────────
# Buddy imports
# ─────────────────────────────────────────────────────────────────────────────
from buddy.models.openai import OpenAIChat
from buddy.models.anthropic import Claude
from buddy.models.token_budget import TokenBudgetConfig
from buddy.models.effort import EffortConfig
from buddy.models.thinking import ThinkingConfig
from buddy.models.multilingual import MultilingualConfig
from buddy.models.cache import PromptCacheConfig
from buddy.models.fast_mode import FastModeConfig
from buddy.agent import (
    Agent,
    RunEvent,
    RunResponseContentEvent,
    RunResponseCompletedEvent,  # noqa: F401  (exported for completeness)
    ToolCallStartedEvent,
    ToolCallCompletedEvent,
    ReasoningStartedEvent,
    ReasoningStepEvent,
    ReasoningCompletedEvent,
    MemoryUpdateStartedEvent,
    MemoryUpdateCompletedEvent,
)
from buddy.memory.v2.memory import Memory
from buddy.memory.v2.db.sqlite import SqliteMemoryDb
from buddy.storage.agent.sqlite import SqliteAgentStorage
from buddy.storage.session.agent import AgentSession
from buddy.team import Team
from buddy.run.team import TeamRunEvent


def _ensure_agent_session_workflow_compat() -> bool:
    """Patch mixed-version Buddy runtimes whose AgentSession rejects
    ``workflow_session_id``.

    Agent code always passes workflow_session_id=..., but some loaded
    AgentSession dataclasses (stale/editable-install mismatch) omit the field.
    Patch every live AgentSession class object used by storage + agent modules.
    """
    import inspect
    import buddy.agent.agent as _agent_mod
    import buddy.storage.session.agent as _sess_mod

    classes = []
    for cls in (_sess_mod.AgentSession, _agent_mod.AgentSession, AgentSession):
        if cls not in classes:
            classes.append(cls)

    patched_any = False
    for cls in classes:
        if getattr(cls, "_buddy_workflow_session_compat", False):
            continue

        try:
            params = inspect.signature(cls.__init__).parameters
        except (TypeError, ValueError):
            params = {}

        if "workflow_session_id" in params:
            cls._buddy_workflow_session_compat = True
            continue

        original_init = cls.__init__
        original_to_dict = getattr(cls, "to_dict", None)

        def compat_init(self, *args, workflow_session_id=None, _orig=original_init, **kwargs):
            _orig(self, *args, **kwargs)
            self.workflow_session_id = workflow_session_id

        cls.__init__ = compat_init  # type: ignore[method-assign]

        if callable(original_to_dict):
            def compat_to_dict(self, _orig=original_to_dict):
                data = _orig(self)
                data["workflow_session_id"] = getattr(self, "workflow_session_id", None)
                return data

            cls.to_dict = compat_to_dict  # type: ignore[method-assign]

        # from_dict may still pass workflow_session_id= into cls(...); patched
        # __init__ above absorbs it. Also wrap from_dict to be extra-safe.
        original_from_dict = getattr(cls, "from_dict", None)
        if callable(original_from_dict):
            @classmethod
            def compat_from_dict(klass, data, _orig=original_from_dict):
                try:
                    return _orig(data)
                except TypeError as exc:
                    if "workflow_session_id" not in str(exc) or not isinstance(data, dict):
                        raise
                    filtered = {k: v for k, v in data.items() if k != "workflow_session_id"}
                    session = _orig(filtered)
                    if session is not None:
                        try:
                            session.workflow_session_id = data.get("workflow_session_id")
                        except Exception:
                            pass
                    return session

            cls.from_dict = compat_from_dict  # type: ignore[method-assign]

        cls._buddy_workflow_session_compat = True
        patched_any = True

    # Keep module aliases pointing at the (possibly patched) storage class
    _agent_mod.AgentSession = _sess_mod.AgentSession
    return patched_any


_AGENT_SESSION_COMPAT_PATCHED = _ensure_agent_session_workflow_compat()

# ── Compaction ─────────────────────────────────────────────────────────────────
from buddy.agent.compaction import auto_compact, server_compact, client_compact

# ── Context editing (optional — graceful fallback if not available) ──────────────────
try:
    from buddy.agent.context_editing import moderate_editing
    _HAS_CONTEXT_EDITING = True
except ImportError:
    _HAS_CONTEXT_EDITING = False

# ─────────────────────────────────────────────────────────────────────────────
# Persistent memory + session storage
# ─────────────────────────────────────────────────────────────────────────────
_shared_memory_db = SqliteMemoryDb(
    table_name="buddy_memories",
    db_file="buddy_memory.db",
)
_shared_storage = SqliteAgentStorage(
    table_name="buddy_sessions",
    db_file="buddy_sessions.db",
)

# ─────────────────────────────────────────────────────────────────────────────
# Tool loader
# ─────────────────────────────────────────────────────────────────────────────
_tools: list = []
_loaded: list[str] = []

def _try(name: str, factory):
    try:
        _tools.append(factory())
        _loaded.append(name)
    except Exception:
        pass

# ── Server / core ──────────────────────────────────────────────────────────────
try:
    from buddy.tools.server import WebSearchTool, WebFetchTool, CodeExecutionTool
    _try("WebSearch",     lambda: WebSearchTool(max_results=10))
    _try("WebFetch",      lambda: WebFetchTool(max_length=40_000))
    _try("CodeExecution", lambda: CodeExecutionTool(timeout=90))
except ImportError:
    pass
try:
    from buddy.tools.bash_tool   import BashTool;       _try("Bash",       lambda: BashTool(timeout=120))
except ImportError: pass
try:
    from buddy.tools.text_editor import TextEditorTool; _try("TextEditor", lambda: TextEditorTool())
except ImportError: pass
try:
    from buddy.tools.memory_tool import MemoryTool;     _try("MemTool",    lambda: MemoryTool())
except ImportError: pass

# ── Code / compute ─────────────────────────────────────────────────────────────
_try("Python",      lambda: __import__("buddy.tools.python",            fromlist=["PythonTools"]).PythonTools(run_code=True, save_and_run=True, pip_install=True))
_try("Calculator",  lambda: __import__("buddy.tools.calculator",        fromlist=["CalculatorTools"]).CalculatorTools(enable_all=True))
_try("Shell",       lambda: __import__("buddy.tools.shell",             fromlist=["ShellTools"]).ShellTools())
_try("Pandas",      lambda: __import__("buddy.tools.pandas",            fromlist=["PandasTools"]).PandasTools())

# ── File system ────────────────────────────────────────────────────────────────
_try("Files",       lambda: __import__("buddy.tools.file",              fromlist=["FileTools"]).FileTools())
_try("LocalFS",     lambda: __import__("buddy.tools.local_file_system", fromlist=["LocalFileSystemTools"]).LocalFileSystemTools(base_dir=os.getcwd()))
_try("CSV",         lambda: __import__("buddy.tools.csv_toolkit",       fromlist=["CsvTools"]).CsvTools())
_try("Excel",       lambda: __import__("buddy.tools.excel",             fromlist=["ExcelTools"]).ExcelTools())

# ── Web / search ───────────────────────────────────────────────────────────────
_try("DuckDuckGo",  lambda: __import__("buddy.tools.duckduckgo",        fromlist=["DuckDuckGoTools"]).DuckDuckGoTools())
_try("Tavily",      lambda: __import__("buddy.tools.tavily",            fromlist=["TavilyTools"]).TavilyTools())
_try("Serper",      lambda: __import__("buddy.tools.serper",            fromlist=["SerperTools"]).SerperTools())
_try("GoogleSearch",lambda: __import__("buddy.tools.googlesearch",      fromlist=["GoogleSearchTools"]).GoogleSearchTools())
_try("Wikipedia",   lambda: __import__("buddy.tools.wikipedia",         fromlist=["WikipediaTools"]).WikipediaTools())
_try("WebBrowser",  lambda: __import__("buddy.tools.webbrowser",        fromlist=["WebBrowserTools"]).WebBrowserTools())
_try("Website",     lambda: __import__("buddy.tools.website",           fromlist=["WebsiteTools"]).WebsiteTools())
_try("Newspaper",   lambda: __import__("buddy.tools.newspaper4k",       fromlist=["Newspaper4k"]).Newspaper4k())
_try("YouTube",     lambda: __import__("buddy.tools.youtube",           fromlist=["YouTubeTools"]).YouTubeTools())

# ── Finance ────────────────────────────────────────────────────────────────────
_try("Finance",     lambda: __import__("buddy.tools.finance",           fromlist=["YFinanceTools"]).YFinanceTools(
    stock_price=True, company_news=True, analyst_recommendations=True,
    company_info=True, technical_indicators=True, historical_prices=True,
))

# ── Productivity ───────────────────────────────────────────────────────────────
_try("GitHub",      lambda: __import__("buddy.tools.github",            fromlist=["GithubTools"]).GithubTools())
_try("Email",       lambda: __import__("buddy.tools.email",             fromlist=["EmailTools"]).EmailTools())
_try("Gmail",       lambda: __import__("buddy.tools.gmail",             fromlist=["GmailTools"]).GmailTools())
_try("Slack",       lambda: __import__("buddy.tools.slack",             fromlist=["SlackTools"]).SlackTools())
_try("Jira",        lambda: __import__("buddy.tools.jira",              fromlist=["JiraTools"]).JiraTools())
_try("Linear",      lambda: __import__("buddy.tools.linear",            fromlist=["LinearTools"]).LinearTools())
_try("MsTeams",     lambda: __import__("buddy.tools.microsoft_teams",   fromlist=["MicrosoftTeamsTools"]).MicrosoftTeamsTools())
_try("GoogleCal",   lambda: __import__("buddy.tools.googlecalendar",    fromlist=["GoogleCalendarTools"]).GoogleCalendarTools())
_try("GSheets",     lambda: __import__("buddy.tools.googlesheets",      fromlist=["GoogleSheetsTools"]).GoogleSheetsTools())

# ── Utilities ──────────────────────────────────────────────────────────────────
_try("OpenWeather", lambda: __import__("buddy.tools.openweather",       fromlist=["OpenWeatherTools"]).OpenWeatherTools())
_try("Timezone",    lambda: __import__("buddy.tools.timezone",          fromlist=["TimezoneTools"]).TimezoneTools())
_try("Translation", lambda: __import__("buddy.tools.translation",       fromlist=["TranslationTools"]).TranslationTools())
_try("IpGeo",       lambda: __import__("buddy.tools.ip_geolocation",    fromlist=["IpGeolocationTools"]).IpGeolocationTools())
_try("QRCode",      lambda: __import__("buddy.tools.qr_code_generator", fromlist=["QRCodeTools"]).QRCodeTools())
_try("Sleep",       lambda: __import__("buddy.tools.sleep",             fromlist=["SleepTool"]).SleepTool())
_try("Docker",      lambda: __import__("buddy.tools.docker",            fromlist=["DockerTools"]).DockerTools())
_try("Thinking",    lambda: __import__("buddy.tools.thinking",          fromlist=["ThinkingTools"]).ThinkingTools())
_try("Reasoning",   lambda: __import__("buddy.tools.reasoning",         fromlist=["ReasoningTools"]).ReasoningTools())
_try("Planning",    lambda: __import__("buddy.tools.planning",          fromlist=["PlanningTools"]).PlanningTools())

# ── AI / Generation ────────────────────────────────────────────────────────────
_try("DallE",       lambda: __import__("buddy.tools.dalle",              fromlist=["DalleTools"]).DalleTools())
_try("ElevenLabs",  lambda: __import__("buddy.tools.eleven_labs",        fromlist=["ElevenLabsTools"]).ElevenLabsTools())

# ── Database ───────────────────────────────────────────────────────────────────
_try("Postgres",    lambda: __import__("buddy.tools.postgres",           fromlist=["PostgresTools"]).PostgresTools())
_try("SQL",         lambda: __import__("buddy.tools.sql",                fromlist=["SqlTools"]).SqlTools())

# ── DevOps / Cloud ─────────────────────────────────────────────────────────────
_try("Kubernetes",  lambda: __import__("buddy.tools.kubernetes_tools",   fromlist=["KubernetesTools"]).KubernetesTools())
_try("AWS",         lambda: __import__("buddy.tools.aws_tools",          fromlist=["AWSTools"]).AWSTools())
_try("AWSLambda",   lambda: __import__("buddy.tools.aws_lambda",        fromlist=["AWSLambdaTools"]).AWSLambdaTools())

# ── Browser automation ─────────────────────────────────────────────────────────
_try("Selenium",    lambda: __import__("buddy.tools.selenium_tool",      fromlist=["SeleniumTools"]).SeleniumTools())

# ── Comms / Social ─────────────────────────────────────────────────────────────
_try("Zoom",        lambda: __import__("buddy.tools.zoom",               fromlist=["ZoomTools"]).ZoomTools())
_try("Confluence",  lambda: __import__("buddy.tools.confluence",         fromlist=["ConfluenceTools"]).ConfluenceTools())
_try("Bitbucket",   lambda: __import__("buddy.tools.bitbucket",          fromlist=["BitbucketTools"]).BitbucketTools())

# ── Visualization / Reporting ──────────────────────────────────────────────────
_try("Report",      lambda: __import__("buddy.tools.report",             fromlist=["ReportTools"]).ReportTools())
_try("Viz",         lambda: __import__("buddy.tools.visualization",      fromlist=["VisualizationTools"]).VisualizationTools())

# ── Maps / Geo ─────────────────────────────────────────────────────────────────
_try("GoogleMaps",  lambda: __import__("buddy.tools.google_maps",        fromlist=["GoogleMapsTools"]).GoogleMapsTools())
_try("SerpApi",     lambda: __import__("buddy.tools.serpapi",             fromlist=["SerpApiTools"]).SerpApiTools())

# ── Misc ───────────────────────────────────────────────────────────────────────
_try("Giphy",       lambda: __import__("buddy.tools.giphy",              fromlist=["GiphyTools"]).GiphyTools())
_try("TodoTools",   lambda: __import__("buddy.tools.todo",               fromlist=["TodoTools"]).TodoTools())

print(f"  Tools loaded ({len(_loaded)}): {', '.join(_loaded)}")
# Each toolkit expands into multiple function schemas. OpenAI hard-caps at 128
# tools per request; buddy auto-defers overflow and injects search_tools.
_fn_est = sum(len(getattr(t, "functions", {}) or {}) for t in _tools)
print(f"  Function schemas (approx): {_fn_est}"
      + ("  [will defer overflow + ToolSearchTool for OpenAI 128 limit]" if _fn_est > 128 else ""))
print()

# ─────────────────────────────────────────────────────────────────────────────
# Model builder
# Assembles an OpenAIChat or Claude model with all dynamic configs applied.
# ─────────────────────────────────────────────────────────────────────────────
def build_model(
    model_id:     str,
    prov:         str,
    ctx_k:        int,
    out_k:        int,
    sup_effort:   bool,
    sup_thinking: bool,
    is_reasoning: bool,
    effort_level: str = "high",
    thinking_mode: str = "adaptive",
    language:     Optional[str] = None,
):
    """
    Build a buddy model wired with the framework's first-class model configs
    (models/ folder): TokenBudgetConfig, EffortConfig, ThinkingConfig,
    MultilingualConfig, PromptCacheConfig, FastModeConfig + refusal fallback.

    effort_level  : "low" | "medium" | "high" | "xhigh" | "max"
    thinking_mode : "adaptive" | "extended" | "disabled"
    """
    # Token budget: reserve 20% for output; compress when 80% of input is used
    max_input = int(ctx_k * 1000 * 0.80)
    token_budget = TokenBudgetConfig(
        max_input_tokens=max_input,
        auto_compress=True,
        warn_at=0.80,
        count_method="approx",
    )
    # First-class effort (models/effort.py): native output_config on Claude,
    # native reasoning_effort on OpenAI reasoning models, prompt-hint injection
    # everywhere else — one config, autonomous per-task via the router.
    effort_cfg = EffortConfig(level=effort_level, inject_prompt=True)
    # Autonomous multilingual (models/multilingual.py): the meta-agent detects
    # the user's language per task; non-English tasks get an enforced native-
    # speaker response in that language. None/en -> no fragment (cache-friendly).
    multilingual_cfg = (
        MultilingualConfig(language=language, idiomatic=True, enforce=True)
        if language and language.lower() not in ("en", "none") else None
    )
    # Explicit prompt-cache breakpoints (models/cache.py): system + tools +
    # stable history (auto breakpoint) — replaces bare cache_prompt=True.
    cache_cfg = PromptCacheConfig(
        enabled=True, cache_system=True, cache_tools=True,
        cache_history=True, cache_history_mode="auto",
    )

    if prov == "oai":
        kwargs: dict = dict(
            id=model_id,
            token_budget=token_budget,
            multilingual=multilingual_cfg,
            prompt_cache_config=cache_cfg,
        )
        max_out = out_k * 1000  # use catalogue limit (no artificial hard-cap)
        if not is_reasoning:
            # Prompt-hint effort for non-reasoning models (reasoning models
            # use the native reasoning_effort param instead — no double-apply).
            kwargs["effort"] = effort_cfg
        if is_reasoning:
            # o-series / gpt-5.x: require max_completion_tokens (not max_tokens);
            # no temperature; control depth via reasoning_effort.
            kwargs["max_completion_tokens"] = max_out
            re_map = {"low": "low", "medium": "medium",
                      "high": "high", "xhigh": "high", "max": "high"}
            kwargs["reasoning_effort"] = re_map.get(effort_level, "high")
        else:
            kwargs["max_tokens"] = max_out
            if OpenAIChat.supports_temperature(model_id):
                kwargs["temperature"] = 0.7
        return OpenAIChat(**kwargs)

    else:  # "ant"
        kwargs: dict = dict(
            id=model_id,
            max_tokens=out_k * 1000,  # catalogue limit (up to 128K on current Claude)
            token_budget=token_budget,
            multilingual=multilingual_cfg,
            prompt_cache_config=cache_cfg,
        )
        if sup_effort:
            # First-class EffortConfig -> output_config for Claude 4.6+
            kwargs["effort"] = effort_cfg
        # Adaptive thinking: supported on Claude 4.6+ (opus/sonnet 4.6, opus/sonnet 5, fable 5)
        # Older models (haiku 4.5, sonnet 4.5) only support extended (budget_tokens) — skip for now
        _ADAPTIVE_PREFIXES = (
            "claude-fable-5", "claude-mythos-5",
            "claude-opus-5",  "claude-sonnet-5",
            "claude-opus-4-8","claude-opus-4-7","claude-opus-4-6",
            "claude-sonnet-4-6",
        )
        model_supports_adaptive = any(model_id.startswith(p) for p in _ADAPTIVE_PREFIXES)
        if sup_thinking and thinking_mode != "disabled" and model_supports_adaptive:
            # First-class ThinkingConfig (models/thinking.py) — validated per
            # model; Claude decides depth, summary streamed back.
            kwargs["thinking_config"] = ThinkingConfig(
                mode="adaptive", display="summarized")
        elif Claude.supports_sampling_params(model_id):
            # Claude 4.7+/5 reject temperature/top_p/top_k entirely. Older
            # non-thinking models still accept temperature; the provider
            # adapter also filters defensively when thinking is on.
            kwargs["temperature"] = 0.7
        # Autonomous fast mode (models/fast_mode.py): on supported Opus models,
        # low/medium-effort tasks run at fast speed with automatic fallback to
        # standard speed on rate limits — router-driven speed/quality tradeoff.
        _fast = FastModeConfig(enabled=True, fallback_on_rate_limit=True)
        if effort_level in ("low", "medium") and _fast.is_supported(model_id):
            kwargs["fast_mode"] = _fast
            print(f"  [Auto] Fast mode ON for {model_id} (effort={effort_level}).",
                  flush=True)
        # Streaming-refusal resilience: auto-retry on a sibling Claude model.
        kwargs["handle_streaming_refusals"] = True
        kwargs["refusal_fallback_model"] = (
            "claude-opus-5" if model_id.startswith("claude-sonnet")
            else "claude-sonnet-5")
        return Claude(**kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Task analyser (auto mode)
# Uses a fast meta-agent to decide model, effort, thinking, and team needs.
# ─────────────────────────────────────────────────────────────────────────────
_CATALOGUE = "\n".join(
    f"  {m[2]:40s}  {m[1]}  tier={m[8]}"
    for m in MODELS
)

_TeamRole = Literal["researcher", "coder", "analyst", "writer", "planner"]

class RoutingDecision(BaseModel):
    """Schema enforced at the API level via structured outputs."""
    model_id:   str   = Field(description="Exact model_id from the catalogue.")
    provider:   Literal["oai", "ant"] = Field(description="'oai' for OpenAI, 'ant' for Anthropic.")
    effort:     Literal["low", "medium", "high", "xhigh", "max"] = Field(
        description="Effort level. Use 'xhigh'/'max' only for genuinely hard problems."
    )
    thinking:   Literal["adaptive", "disabled"] = Field(
        description="'adaptive' to enable extended thinking on supported models, else 'disabled'."
    )
    needs_team: bool  = Field(
        description="True when the task spans multiple domains (research+code+write, etc.)."
    )
    team_roles: List[_TeamRole] = Field(
        default_factory=list,
        description="Specialist roles to include in the team when needs_team is true."
    )
    needs_advisor: bool = Field(
        default=False,
        description="True when the task involves deep strategy, architecture, or "
                    "multi-step planning that benefits from a strategic advisor agent."
    )
    needs_rag: bool = Field(
        default=True,
        description="True when the task may reference project files, prior "
                    "decisions, local documentation, or workspace knowledge. "
                    "False only for clearly self-contained tasks (math, general "
                    "knowledge, web-only lookups)."
    )
    domain: str = Field(
        default="general",
        description="Competency domain of the task: one of 'coding', 'research', "
                    "'writing', 'data', 'planning', 'general'."
    )
    language: str = Field(
        default="en",
        description="ISO 639-1 code of the language the USER wrote in "
                    "(e.g. 'en', 'ta', 'hi', 'fr'). The reply will be enforced "
                    "in this language when it is not English."
    )
    rationale:  str   = Field(description="One-sentence explanation for this routing decision.")


def analyze_task(task: str) -> dict:
    """
    Analyse the task with a fast meta-agent and return config decisions as a dict.
    Uses structured outputs (response_model) — schema is enforced at the API level.
    Falls back to GPT-4o + high effort on any error.
    """
    _defaults: dict = {
        "model_id":   "gpt-4o",
        "provider":   "oai",
        "effort":     "high",
        "thinking":   "adaptive",
        "needs_team": False,
        "team_roles": [],
        "needs_advisor": False,
        "needs_rag":  True,
        "domain":     "general",
        "language":   "en",
        "rationale":  "default fallback",
    }
    try:
        meta_model = OpenAIChat(
            id=_META_ID,
            max_tokens=512,
            temperature=0.0,
        )
        meta_agent = Agent(
            name="TaskAnalyser",
            model=meta_model,
            description=(
                "You are a task-routing assistant. "
                "Given a task description, select the best model and configuration "
                "from the catalogue below and return a structured routing decision.\n\n"
                f"Available models:\n{_CATALOGUE}\n\n"
                "Rules:\n"
                "  Use flagship/balanced tier for hard reasoning, long coding, multi-step agentic work.\n"
                "  Use fast/cheap tier for quick lookups, simple Q&A, short summaries.\n"
                "  Prefer Claude (ant) for long agentic tasks; OpenAI for pure reasoning.\n"
                "  Set effort='xhigh' or 'max' only for genuinely hard problems.\n"
                "  Set effort='low' or 'medium' for simple or conversational tasks.\n"
                "  Set needs_team=true when the task spans multiple domains.\n"
                "  Set needs_advisor=true for deep strategy, architecture reviews, "
                "or complex multi-step planning tasks.\n"
                "  Set needs_rag=false only for self-contained tasks (pure math, "
                "general knowledge, web-only lookups); otherwise keep it true so "
                "the agent can consult workspace knowledge.\n"
                "  Classify the task domain as one of: coding, research, writing, "
                "data, planning, general.\n"
                "  Report the ISO 639-1 code of the language the user wrote in "
                "as 'language' (e.g. en, ta, hi, fr)."
            ),
            response_model=RoutingDecision,
            structured_outputs=True,
            enable_agentic_memory=False,
            enable_session_summaries=False,
            reasoning=False,
            stream=False,
            markdown=False,
        )
        resp = meta_agent.run(f"Task: {task[:600]}")
        # With response_model set, resp.content is a RoutingDecision instance
        decision_obj: RoutingDecision = (
            resp.content if isinstance(resp.content, RoutingDecision) else RoutingDecision.model_validate(
                json.loads(resp.content) if isinstance(resp.content, str) else resp.content
            )
        )
        decision = decision_obj.model_dump()
        # Ensure model_id is actually in our catalogue
        if decision["model_id"] not in MODEL_BY_ID:
            decision["model_id"] = _defaults["model_id"]
            decision["provider"] = _defaults["provider"]
        return decision
    except Exception:
        return _defaults


# ─────────────────────────────────────────────────────────────────────────────
# Agent builder
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# Autonomous RAG — local iRAG knowledge base (SQLite + TF-IDF + ontology).
# No embedding API needed. Ingests workspace docs (.md/.txt) in a background
# thread at first use; agents get agentic RAG (search_knowledge=True) so the
# MODEL decides when to search, and update_knowledge=True so it can save
# new learnings back to the KB autonomously.
# ─────────────────────────────────────────────────────────────────────────────
_kb            = None
_kb_lock       = threading.Lock()
_kb_load_began = False

def _get_knowledge():
    """Lazy singleton KB. Never blocks the chat loop: ingestion runs in a
    daemon thread; searches before load completes simply return fewer docs."""
    global _kb, _kb_load_began
    with _kb_lock:
        if _kb is None:
            try:
                from buddy.knowledge import irag
                _kb = irag(
                    dir_path = os.getcwd(),
                    formats  = [".md", ".txt"],
                    db_path  = "buddy_knowledge.db",
                    instructions = (
                        "Workspace knowledge base: project docs, READMEs and "
                        "notes. Search it when a task references the project, "
                        "prior decisions, or local documentation."
                    ),
                )
            except Exception as exc:
                print(f"  [RAG] Knowledge base unavailable: {exc}")
                _kb = False          # sentinel: don't retry every build
        if _kb and not _kb_load_began:
            _kb_load_began = True
            def _load():
                try:
                    _kb.load(recreate=False)
                    info = {}
                    try:
                        info = _kb.get_database_info() or {}
                    except Exception:
                        pass
                    print(f"\n  [RAG] Knowledge base ready "
                          f"({info.get('total_documents', '?')} docs indexed).",
                          flush=True)
                except Exception as exc:
                    print(f"\n  [RAG] KB ingestion failed: {exc}", flush=True)
            threading.Thread(target=_load, daemon=True).start()
    return _kb or None


# ─────────────────────────────────────────────────────────────────────────────
# Autonomous monitoring & evaluation (buddy.eval + local buddy_metrics.db).
#   • Every run is recorded: latency, tokens, tool calls/errors, escalations.
#   • Reliability is auto-checked per run (failed tool calls are flagged).
#   • CompetencyTracker (buddy.eval.competency_runtime) keeps live per-domain
#     EMA scores from REAL outcomes — persisted across sessions — and feeds an
#     autonomous feedback loop: weak domains get a proactive effort boost.
# ─────────────────────────────────────────────────────────────────────────────
from buddy.eval.competency_runtime import CompetencyTracker

class _Monitor:
    """Local-first run monitor + live competency tracking. No external services."""

    def __init__(self, db_path: str = "buddy_metrics.db"):
        self.db_path = db_path
        self.escalations_this_run = 0
        con = self._con()
        con.execute(
            "CREATE TABLE IF NOT EXISTS runs("
            "ts REAL, task TEXT, model_id TEXT, effort TEXT, thinking TEXT, "
            "is_team INTEGER, advisor INTEGER, rag INTEGER, domain TEXT, "
            "duration_s REAL, input_tokens INTEGER, output_tokens INTEGER, "
            "total_tokens INTEGER, tool_calls INTEGER, tool_errors INTEGER, "
            "escalations INTEGER, status TEXT)"
        )
        con.execute(
            "CREATE TABLE IF NOT EXISTS competency("
            "domain TEXT PRIMARY KEY, score REAL, observations INTEGER)"
        )
        con.commit()
        seed = {r[0]: r[1] for r in con.execute("SELECT domain, score FROM competency")}
        con.close()
        # Live per-domain competency (EMA over real outcomes), reseeded from disk
        self.tracker = CompetencyTracker(base=10.0, alpha=0.3, seed=seed or None)

    def _con(self):
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _run_stats(runner):
        """Best-effort extraction of tokens + tool stats from the last RunResponse."""
        rr = getattr(runner, "run_response", None)
        inp = out = tot = calls = errs = 0
        if rr is not None:
            m = getattr(rr, "metrics", None) or {}
            def _sum(key):
                v = m.get(key) if isinstance(m, dict) else None
                if isinstance(v, (list, tuple)):
                    return int(sum(x or 0 for x in v))
                try:
                    return int(v or 0)
                except (TypeError, ValueError):
                    return 0
            inp = _sum("input_tokens")
            out = _sum("output_tokens")
            tot = _sum("total_tokens") or (inp + out)
            tools = getattr(rr, "tools", None) or []
            calls = len(tools)
            for t in tools:
                err = (t.get("tool_call_error") if isinstance(t, dict)
                       else getattr(t, "tool_call_error", None))
                if err:
                    errs += 1
        return inp, out, tot, calls, errs

    def record(self, task: str, sess, dec: dict, duration_s: float, status: str):
        """Record one run outcome; updates competency + reliability signals."""
        dec = dec or {}
        domain = dec.get("domain", "general") or "general"
        inp, out, tot, calls, errs = self._run_stats(sess.runner)
        success = (status == "ok") and errs == 0
        new_score = self.tracker.record_outcome(domain, success)
        try:
            con = self._con()
            con.execute(
                "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (time.time(), task[:500], sess.model_id, sess.effort_level,
                 sess.thinking_mode, int(sess.is_team),
                 int(getattr(sess, "_use_advisor", False)),
                 int(dec.get("needs_rag", True)), domain, round(duration_s, 3),
                 inp, out, tot, calls, errs, self.escalations_this_run, status),
            )
            con.execute(
                "INSERT INTO competency(domain, score, observations) VALUES(?,?,?) "
                "ON CONFLICT(domain) DO UPDATE SET score=excluded.score, "
                "observations=excluded.observations",
                (domain, new_score, self.tracker.observations(domain)),
            )
            con.commit()
            con.close()
        except Exception as exc:
            print(f"  [Monitor] metrics write failed: {exc}", flush=True)
        if errs:
            print(f"  [Monitor] Reliability: {errs}/{calls} tool call(s) "
                  f"FAILED this run.", flush=True)
        self.escalations_this_run = 0

    def competency_boost(self, dec: dict) -> None:
        """Autonomous feedback loop: if live competency in this task's domain is
        weak (score < 4/10 over >= 3 real outcomes), proactively boost effort."""
        domain = (dec or {}).get("domain", "general") or "general"
        score  = self.tracker.get(domain)
        obs    = self.tracker.observations(domain)
        if obs >= 3 and score < 4.0:
            nxt = _next_effort(dec.get("effort", "high"))
            if nxt:
                print(f"  [Monitor] Low competency in '{domain}' "
                      f"({score:.1f}/10 over {obs} runs) — boosting effort "
                      f"{dec.get('effort')} -> {nxt}.", flush=True)
                dec["effort"] = nxt

    def summary(self) -> None:
        """Print the /metrics dashboard from buddy_metrics.db."""
        try:
            con = self._con()
            n, ok, avg_d, tok = con.execute(
                "SELECT COUNT(*), SUM(status='ok'), AVG(duration_s), "
                "SUM(total_tokens) FROM runs").fetchone()
            print(f"\n  Runs      : {n or 0}   OK: {ok or 0}   "
                  f"Success: {(100.0*(ok or 0)/n if n else 0):.0f}%")
            print(f"  Avg time  : {(avg_d or 0):.1f}s   Total tokens: {tok or 0}")
            print("  Per model :")
            for mid, c, d in con.execute(
                    "SELECT model_id, COUNT(*), AVG(duration_s) FROM runs "
                    "GROUP BY model_id ORDER BY COUNT(*) DESC LIMIT 8"):
                print(f"    {mid:<28} runs={c:<4} avg={d:.1f}s")
            print("  Competency (live, 0-10):")
            for dom, sc, ob in con.execute(
                    "SELECT domain, score, observations FROM competency "
                    "ORDER BY score ASC"):
                print(f"    {dom:<12} {sc:4.1f}  ({ob} runs)")
            esc, terr = con.execute(
                "SELECT SUM(escalations), SUM(tool_errors) FROM runs").fetchone()
            print(f"  Self-heals: {esc or 0} effort escalations   "
                  f"Tool errors: {terr or 0}\n")
            con.close()
        except Exception as exc:
            print(f"  [Monitor] summary failed: {exc}\n")

_MON = _Monitor()


def build_agent(
    model_id:      str,
    prov:          str,
    ctx_k:         int,
    out_k:         int,
    sup_effort:    bool,
    sup_thinking:  bool,
    is_reasoning:  bool,
    effort_level:  str = "high",
    thinking_mode: str = "adaptive",
    session_id:    Optional[str] = None,
    name:          str = "Buddy",
    role:          Optional[str] = None,
    use_advisor:   bool = False,        # Strategic advisor for complex reasoning
    use_compaction: bool = True,        # Auto conversation compaction
    use_rag:       bool = True,         # Agentic RAG over workspace knowledge
    language:      Optional[str] = None,  # user language (meta-agent detected)
) -> Agent:
    model = build_model(
        model_id, prov, ctx_k, out_k,
        sup_effort, sup_thinking, is_reasoning,
        effort_level, thinking_mode,
        language=language,
    )
    memory = Memory(model=model, db=_shared_memory_db)

    # ── Advisor ───────────────────────────────────────────────────────────────────
    # advisor=True → auto-selects best advisor model (Claude Opus 5 for OAI, native for Claude)
    advisor_cfg = True if use_advisor else None

    # ── Compaction ────────────────────────────────────────────────────────────────
    # Auto compaction: server-side for Claude 4.6+, client-side fallback for others
    compaction_cfg = None
    if use_compaction:
        try:
            compaction_cfg = auto_compact(
                trigger_at_pct=0.75,
                min_messages_to_keep=6,
                summary_max_tokens=2048,
            )
        except Exception:
            compaction_cfg = None

    # ── Context editing ───────────────────────────────────────────────────────────
    ctx_editing = None
    if _HAS_CONTEXT_EDITING:
        try:
            ctx_editing = moderate_editing()
        except Exception:
            ctx_editing = None

    # ── Agentic RAG ───────────────────────────────────────────────────────────────
    # knowledge + search_knowledge=True → the MODEL decides when to search the KB
    # update_knowledge=True             → the agent saves new learnings to the KB
    knowledge_cfg = _get_knowledge() if use_rag else None

    persona = role or (
        "You are Buddy, an elite autonomous AI agent. "
        "You can browse the web, write and execute code, read/write files, "
        "query finance data, call APIs, run shell commands, search Wikipedia, "
        "translate text, check weather, and much more. "
        "You learn about the user persistently across sessions via memory. "
        "You NEVER give up — you keep using tools, reasoning, and retrying until "
        "the task is fully and correctly completed."
    )

    return Agent(
        name=name,
        model=model,
        tools=_tools,
        # Memory + persistence
        memory=memory,
        storage=_shared_storage,
        session_id=session_id,
        enable_agentic_memory=True,
        enable_user_memories=True,
        enable_session_summaries=False,   # disable: triggers ModelResponse.extra_data bug
        add_memory_references=True,
        # Conversation history
        add_history_to_messages=True,
        num_history_runs=30,
        search_previous_sessions_history=True,
        # Agentic RAG — agent autonomously searches & updates the workspace KB
        knowledge=knowledge_cfg,
        search_knowledge=bool(knowledge_cfg),
        update_knowledge=bool(knowledge_cfg),
        # Reasoning: disabled at agent-loop level — models reason natively
        # (reasoning=True triggers a ModelResponse.extra_data bug in this buddy build)
        reasoning=False,
        # Reliability
        retries=3,
        delay_between_retries=2,
        exponential_backoff=True,
        tool_call_limit=80,
        # Tool behaviour — defer overflow past OpenAI's 128-tool limit via search_tools
        manage_tool_context=True,
        auto_tool_selection=True,        # model autonomously decides tool usage
        show_tool_calls=True,
        read_tool_call_history=True,
        # Prompt caching (Anthropic cache_control / OpenAI automatic)
        cache_prompt=True,
        # Output
        markdown=True,
        stream=True,
        add_datetime_to_instructions=True,
        add_context=True,
        context={
            "workspace": os.getcwd(),
            "python":    sys.version.split()[0],
            "platform":  sys.platform,
            "model_id":  model_id,
            "provider":  prov,
            "effort":    effort_level,
            "thinking":  thinking_mode,
            "user":      "Sriram",
        },
        # Persona
        description=persona,
        goal="Fully accomplish the user's task with high quality and accuracy.",
        instructions=[
            "Think step-by-step before every response.",
            "Use tools proactively — never guess when you can look it up or run code.",
            "Show all tool outputs and intermediate results.",
            "If one approach fails, immediately try a different tool or strategy.",
            "For multi-step tasks, decompose and complete each step in order.",
            "Cite sources and show your work.",
            "Recall relevant context from previous conversations via memory.",
            "Only declare a task complete when the result is verified.",
        ],
        success_criteria=(
            "The task is fully accomplished, verified, and the user's question "
            "is completely answered."
        ),
        # Advisor
        advisor=advisor_cfg,
        # Compaction
        compaction=compaction_cfg,
        # Context editing (trims old tool results, thinking blocks)
        context_editing=ctx_editing,
        # Additional
        user_id="sriram",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Team builder
# Creates an autonomous specialist team for complex multi-domain tasks.
# ─────────────────────────────────────────────────────────────────────────────
_SPECIALIST_CFG = {
    "researcher": {
        "desc":         "Expert researcher: web search, fact-finding, Wikipedia, news gathering.",
        "model_id":     "gpt-4.1",    "prov": "oai",
        "ctx_k": 1048,  "out_k": 32,
        "sup_effort":   False, "sup_thinking": False, "is_reasoning": False,
        "effort":       "high",        "thinking": "disabled",
    },
    "coder": {
        "desc":         "Expert software engineer: writes, executes, and debugs code.",
        "model_id":     "claude-sonnet-4-6", "prov": "ant",
        "ctx_k": 1000,  "out_k": 128,
        "sup_effort":   True,  "sup_thinking": True,  "is_reasoning": False,
        "effort":       "high",        "thinking": "adaptive",
    },
    "analyst": {
        "desc":         "Expert data analyst: statistics, finance, numerical modeling.",
        "model_id":     "gpt-4o",     "prov": "oai",
        "ctx_k": 128,   "out_k": 16,
        "sup_effort":   False, "sup_thinking": False, "is_reasoning": False,
        "effort":       "high",        "thinking": "disabled",
    },
    "writer": {
        "desc":         "Expert writer and editor: prose, reports, documentation.",
        "model_id":     "claude-sonnet-4-6", "prov": "ant",
        "ctx_k": 1000,  "out_k": 128,
        "sup_effort":   True,  "sup_thinking": True,  "is_reasoning": False,
        "effort":       "medium",      "thinking": "adaptive",
    },
    "planner": {
        "desc":         "Expert strategist: task decomposition, planning, orchestration.",
        "model_id":     "claude-opus-4-6", "prov": "ant",
        "ctx_k": 1000,  "out_k": 128,
        "sup_effort":   True,  "sup_thinking": True,  "is_reasoning": False,
        "effort":       "xhigh",       "thinking": "adaptive",
    },
}


def build_team(
    roles:        list[str],
    effort_level: str = "high",
    session_id:   Optional[str] = None,
) -> Team:
    """Build an autonomous specialist Team with a strong coordinator model."""
    members: list = []
    for role in roles:
        cfg = _SPECIALIST_CFG.get(role)
        if cfg is None:
            continue
        members.append(build_agent(
            model_id     = cfg["model_id"],
            prov         = cfg["prov"],
            ctx_k        = cfg["ctx_k"],
            out_k        = cfg["out_k"],
            sup_effort   = cfg["sup_effort"],
            sup_thinking = cfg["sup_thinking"],
            is_reasoning = cfg["is_reasoning"],
            effort_level = cfg["effort"],
            thinking_mode= cfg["thinking"],
            session_id   = None,
            name         = f"Buddy-{role.capitalize()}",
            role         = cfg["desc"],
            use_advisor  = False,       # advisors on individual members would be expensive
            use_compaction = True,      # each member gets compaction
        ))

    if not members:
        for r in ("researcher", "coder"):
            cfg = _SPECIALIST_CFG[r]
            members.append(build_agent(
                model_id=cfg["model_id"], prov=cfg["prov"],
                ctx_k=cfg["ctx_k"],      out_k=cfg["out_k"],
                sup_effort=cfg["sup_effort"], sup_thinking=cfg["sup_thinking"],
                is_reasoning=cfg["is_reasoning"],
                effort_level=cfg["effort"], thinking_mode=cfg["thinking"],
                session_id=None, name=f"Buddy-{r.capitalize()}", role=cfg["desc"],
                use_advisor=False, use_compaction=True,
            ))

    # Coordinator: powerful long-context model
    cc = _SPECIALIST_CFG["planner"]
    coord_model = build_model(
        model_id     = cc["model_id"],
        prov         = cc["prov"],
        ctx_k        = cc["ctx_k"],
        out_k        = cc["out_k"],
        sup_effort   = cc["sup_effort"],
        sup_thinking = cc["sup_thinking"],
        is_reasoning = cc["is_reasoning"],
        effort_level = effort_level,
        thinking_mode= cc["thinking"],
    )

    member_names = ", ".join(getattr(m, "name", str(m)) for m in members)
    return Team(
        name="Buddy-Team",
        members=members,
        mode="coordinate",
        model=coord_model,
        session_id=session_id,
        storage=_shared_storage,
        description=(
            f"Autonomous specialist team: {member_names}. "
            "Collaborates to fully accomplish complex multi-domain tasks. "
            "Coordinator synthesises all member outputs into one complete answer."
        ),
        instructions=[
            "Decompose the task and delegate sub-tasks to the best-fit specialist.",
            "Run specialists in parallel where independent.",
            "Synthesise all member outputs into one coherent, verified final answer.",
            "The task is only complete when every sub-goal is confirmed delivered.",
        ],
        success_criteria=(
            "All sub-goals verified and the final answer is coherent and complete."
        ),
        memory=Memory(model=coord_model, db=_shared_memory_db),
        enable_agentic_memory=True,
        enable_user_memories=True,
        enable_session_summaries=False,   # disable: triggers ModelResponse.extra_data bug
        add_memory_references=True,
        markdown=True,
        stream=True,
        stream_member_events=True,
        show_tool_calls=True,
        tool_call_limit=80,
        manage_tool_context=True,
        add_datetime_to_instructions=True,
        reasoning=False,                  # disable: triggers ModelResponse.extra_data bug
        # Context (Team-level)
        add_context=True,
        context={
            "workspace": os.getcwd(),
            "python":    sys.version.split()[0],
            "platform":  sys.platform,
            "user":      "Sriram",
        },
        # Team collaboration features
        enable_agentic_context=True,
        share_member_interactions=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
class _Session:
    def __init__(self):
        self.runner        = None   # Agent | Team
        self.is_team       = False
        self.model_id      = _sel_id
        self.prov          = _sel_prov
        self.label         = _sel_label
        self.ctx_k         = _sel_ctx
        self.out_k         = _sel_out
        self.sup_effort    = _sel_eff
        self.sup_thinking  = _sel_thnk
        self.is_reasoning  = _sel_rsn
        self.tier          = _sel_tier
        self.effort_level  = "high"
        self.thinking_mode = "adaptive"
        self.analysis      = {}
        self.session_id    = None
        self._use_advisor  = False

    def init_fixed(self):
        """Create a fixed-model Agent (non-auto mode)."""
        self.runner = build_agent(
            model_id     = self.model_id,
            prov         = self.prov,
            ctx_k        = self.ctx_k,
            out_k        = self.out_k,
            sup_effort   = self.sup_effort,
            sup_thinking = self.sup_thinking,
            is_reasoning = self.is_reasoning,
            effort_level = self.effort_level,
            thinking_mode= self.thinking_mode,
            session_id   = self.session_id,
            use_advisor  = self._use_advisor,
            use_compaction = True,
        )
        self.is_team = False
        if self.session_id is None:
            self.session_id = getattr(self.runner, "session_id", None)

    def _config_signature(self, dec: dict) -> tuple:
        """Hashable signature of a routing decision — used to detect when a
        rebuild (auto-switch) is actually required."""
        return (
            dec.get("model_id"),
            dec.get("effort"),
            dec.get("thinking"),
            bool(dec.get("needs_team")),
            tuple(sorted(dec.get("team_roles") or [])),
            bool(dec.get("needs_advisor")),
            bool(dec.get("needs_rag", True)),
            (dec.get("language") or "en").lower(),
        )

    def init_auto(self, task: str):
        """Autonomously route EVERY task: analyse it, then switch model /
        effort / thinking / team / advisor as needed. Reuses the existing
        runner when the optimal configuration is unchanged (preserves the
        in-flight conversation); session_id persists across switches."""
        print("  [Auto] Analysing task...", flush=True)
        dec = analyze_task(task)
        if _rag_pin is not None:          # user-pinned RAG overrides routing
            dec["needs_rag"] = _rag_pin

        # Autonomous feedback loop: boost effort in domains with weak live
        # competency (learned from real run outcomes, persisted on disk).
        _MON.competency_boost(dec)

        new_sig  = self._config_signature(dec)
        prev_sig = self._config_signature(self.analysis) if self.analysis else None
        self.analysis = dec

        if self.runner is not None and new_sig == prev_sig:
            print("  [Auto] Routing unchanged — reusing current runner.\n", flush=True)
            return

        if self.runner is not None and prev_sig is not None:
            print(f"  [Auto] Switching: {prev_sig[0]} -> {new_sig[0]}", flush=True)

        mid = dec.get("model_id", "gpt-4o")
        m   = MODEL_BY_ID.get(mid) or MODEL_BY_ID.get("gpt-4o")
        if m:
            (self.label, self.prov, self.model_id,
             self.ctx_k, self.out_k, self.sup_effort,
             self.sup_thinking, self.is_reasoning,
             self.tier) = m
        self.effort_level  = dec.get("effort",   "high")
        self.thinking_mode = dec.get("thinking", "adaptive")
        self._use_advisor  = bool(dec.get("needs_advisor", False))

        print(
            f"  [Auto] Model: {self.model_id}  effort={self.effort_level}  "
            f"thinking={self.thinking_mode}  advisor={'ON' if self._use_advisor else 'OFF'}  "
            f"rag={'ON' if dec.get('needs_rag', True) else 'OFF'}"
            + (f"  lang={dec.get('language')}"
               if (dec.get('language') or 'en').lower() != 'en' else ""),
            flush=True,
        )

        if dec.get("needs_team") and dec.get("team_roles"):
            roles = dec["team_roles"]
            print(f"  [Auto] Forming team: {', '.join(roles)}", flush=True)
            self.runner  = build_team(roles, self.effort_level, self.session_id)
            self.is_team = True
        else:
            self.runner = build_agent(
                model_id     = self.model_id,
                prov         = self.prov,
                ctx_k        = self.ctx_k,
                out_k        = self.out_k,
                sup_effort   = self.sup_effort,
                sup_thinking = self.sup_thinking,
                is_reasoning = self.is_reasoning,
                effort_level = self.effort_level,
                thinking_mode= self.thinking_mode,
                session_id   = self.session_id,
                use_advisor  = self._use_advisor,
                use_compaction = True,
                use_rag      = bool(dec.get("needs_rag", True)),
                language     = dec.get("language", "en"),
            )
            self.is_team = False

        if self.session_id is None:
            self.session_id = getattr(self.runner, "session_id", None)

        rationale = dec.get("rationale", "")
        if rationale:
            print(f"  [Auto] {rationale}", flush=True)
        print()


_rag_pin: Optional[bool] = None   # None = autonomous (meta-agent decides per task)
_last_task: Optional[str] = None  # last user task (for /eval on the last answer)

_sess = _Session()
if not AUTO_MODE:
    _sess.init_fixed()


# ─────────────────────────────────────────────────────────────────────────────
# Event-value sets (module-level, computed once)
# Both RunEvent and TeamRunEvent are str-enums so their .value is a plain str.
# Using string values directly avoids any enum-attribute lookup at call time.
# ─────────────────────────────────────────────────────────────────────────────
_EV_REASONING_START = {RunEvent.reasoning_started.value,   TeamRunEvent.reasoning_started.value}
_EV_REASONING_STEP  = {RunEvent.reasoning_step.value,      TeamRunEvent.reasoning_step.value}
_EV_REASONING_END   = {RunEvent.reasoning_completed.value, TeamRunEvent.reasoning_completed.value}
_EV_TOOL_START      = {RunEvent.tool_call_started.value,   TeamRunEvent.tool_call_started.value}
_EV_TOOL_END        = {RunEvent.tool_call_completed.value, TeamRunEvent.tool_call_completed.value}
_EV_MEM_START       = {RunEvent.memory_update_started.value,   TeamRunEvent.memory_update_started.value}
_EV_MEM_END         = {RunEvent.memory_update_completed.value, TeamRunEvent.memory_update_completed.value}
_EV_CONTENT         = {RunEvent.run_response_content.value, TeamRunEvent.run_response_content.value}
_EV_COMPLETE        = {RunEvent.run_completed.value,        TeamRunEvent.run_completed.value}

# ─────────────────────────────────────────────────────────────────────────────
# Streaming output handler
# Handles both Agent (RunEvent) and Team (TeamRunEvent) event streams.
# ─────────────────────────────────────────────────────────────────────────────
def _stream_once(user_input: str) -> None:
    """Single streaming attempt. Hard failures propagate so the autonomous
    self-healing wrapper (_stream) can escalate effort and retry."""
    run = _sess.runner.run(user_input, stream=True)

    in_thinking  = False
    in_reasoning = False
    printed_hdr  = False
    last_tool    = None
    runner_name  = "Team" if _sess.is_team else "Buddy"

    try:
        for event in run:
            etype = getattr(event, "event", None)

            # ── Reasoning ─────────────────────────────────────────────────────────────────
            if etype in _EV_REASONING_START:
                print("[Reasoning...]", flush=True)
                in_reasoning = True

            elif etype in _EV_REASONING_STEP:
                step = (getattr(event, "content", "") or
                        getattr(event, "reasoning_content", "") or "")
                if step:
                    print(f"  >> {str(step)[:240]}", flush=True)

            elif etype in _EV_REASONING_END:
                if in_reasoning:
                    print()
                in_reasoning = False

            # ── Tool calls ────────────────────────────────────────────────────────────────
            elif etype in _EV_TOOL_START:
                tool_obj = getattr(event, "tool", None)
                if tool_obj:
                    tname = getattr(tool_obj, "name", "tool")
                    targs = str(getattr(tool_obj, "arguments", ""))[:120].replace("\n", " ")
                else:
                    tname = getattr(event, "tool_name", "tool")
                    targs = str(getattr(event, "tool_args", ""))[:120].replace("\n", " ")
                last_tool = tname
                print(f"\n[Tool: {tname}]  {targs}", flush=True)

            elif etype in _EV_TOOL_END:
                tool_obj = getattr(event, "tool", None)
                tname    = (getattr(tool_obj, "name", None) if tool_obj
                            else None) or last_tool or "tool"
                result   = (getattr(event, "content", "")
                            or (str(getattr(tool_obj, "result", "")) if tool_obj else ""))
                rstr     = str(result)
                preview  = rstr[:300].replace("\n", " ")
                if len(rstr) > 300:
                    preview += f"  … ({len(rstr)} chars)"
                print(f"[/{tname}]  {preview}", flush=True)

            # ── Memory updates ────────────────────────────────────────────────────────────
            elif etype in _EV_MEM_START:
                print("[Memory: updating...]", flush=True)

            elif etype in _EV_MEM_END:
                print("[Memory: updated]", flush=True)

            # ── Content streaming ─────────────────────────────────────────────────────────
            elif etype in _EV_CONTENT:
                content  = getattr(event, "content",  "") or ""
                thinking = getattr(event, "thinking", None)

                if thinking and not in_thinking:
                    print("\n[Thinking]", flush=True)
                    in_thinking = True
                if thinking:
                    print(thinking, end="", flush=True)

                if content:
                    if in_thinking:
                        print("\n[/Thinking]\n", flush=True)
                        in_thinking = False
                    if not printed_hdr:
                        print(f"{runner_name}: ", end="", flush=True)
                        printed_hdr = True
                    print(content, end="", flush=True)

            # ── Run complete ──────────────────────────────────────────────────────────────
            elif etype in _EV_COMPLETE:
                if in_thinking:
                    print("\n[/Thinking]", flush=True)
                    in_thinking = False
                if not printed_hdr:
                    content = getattr(event, "content", "") or ""
                    if content:
                        print(f"{runner_name}: {content}", end="", flush=True)
                break

    except KeyboardInterrupt:
        print("\n[interrupted]")

    print("\n", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# Autonomous self-healing — adaptive effort escalation.
# If a run fails, Buddy automatically boosts effort one rung up the ladder,
# rebuilds the runner (same session — conversation preserved), and retries.
# ─────────────────────────────────────────────────────────────────────────────
_EFFORT_LADDER = ["low", "medium", "high", "xhigh", "max"]

def _next_effort(cur: str) -> Optional[str]:
    try:
        i = _EFFORT_LADDER.index(cur)
    except ValueError:
        return "high"
    return _EFFORT_LADDER[i + 1] if i + 1 < len(_EFFORT_LADDER) else None


def _escalate_and_rebuild(reason: str) -> bool:
    """Boost effort one level and rebuild the runner. Returns True if escalated."""
    nxt = _next_effort(_sess.effort_level)
    if nxt is None:
        return False
    print(f"  [Auto-Heal] {reason}", flush=True)
    print(f"  [Auto-Heal] Escalating effort {_sess.effort_level} -> {nxt}; "
          f"rebuilding runner (session preserved).", flush=True)
    _MON.escalations_this_run += 1
    _sess.effort_level = nxt
    if isinstance(_sess.analysis, dict):
        _sess.analysis["effort"] = nxt
    try:
        if _sess.is_team and (_sess.analysis or {}).get("team_roles"):
            _sess.runner = build_team(
                _sess.analysis["team_roles"], nxt, _sess.session_id)
        else:
            _sess.runner = build_agent(
                model_id     = _sess.model_id,
                prov         = _sess.prov,
                ctx_k        = _sess.ctx_k,
                out_k        = _sess.out_k,
                sup_effort   = _sess.sup_effort,
                sup_thinking = _sess.sup_thinking,
                is_reasoning = _sess.is_reasoning,
                effort_level = nxt,
                thinking_mode= _sess.thinking_mode,
                session_id   = _sess.session_id,
                use_advisor  = getattr(_sess, "_use_advisor", False),
                use_compaction = True,
                use_rag      = bool((_sess.analysis or {}).get("needs_rag", True)),
                language     = (_sess.analysis or {}).get("language", "en"),
            )
        return True
    except Exception as exc:
        print(f"  [Auto-Heal] Rebuild failed: {exc}", flush=True)
        return False


def _stream(user_input: str) -> None:
    """Autonomous run wrapper: routes the task (AUTO mode), then attempts the
    run with up to 2 self-healing effort escalations on hard failure."""
    print()
    if AUTO_MODE:
        _sess.init_auto(user_input)

    global _last_task
    _last_task = user_input
    t0 = time.time()
    max_attempts = 3          # initial try + 2 autonomous escalations
    for attempt in range(1, max_attempts + 1):
        try:
            _stream_once(user_input)
            _MON.record(user_input, _sess, _sess.analysis, time.time() - t0, "ok")
            return
        except KeyboardInterrupt:
            print("\n[interrupted]\n")
            _MON.record(user_input, _sess, _sess.analysis, time.time() - t0,
                        "interrupted")
            return
        except Exception as exc:
            reason = f"Run failed ({type(exc).__name__}: {str(exc)[:160]})"
            if attempt < max_attempts and _escalate_and_rebuild(reason):
                continue
            print(f"Buddy: [ERROR] {exc}\n")
            _MON.record(user_input, _sess, _sess.analysis, time.time() - t0,
                        "error")
            return


# ─────────────────────────────────────────────────────────────────────────────
# Task sources — fully autonomous input handling:
#   1) CLI positional args:   python test.py "task one" "task two"
#   2) Piped stdin (headless): echo "task" | python test.py
#   3) Interactive TTY (only when nothing else is available)
# ─────────────────────────────────────────────────────────────────────────────
def _task_source():
    cli_tasks = [a for a in sys.argv[1:] if not a.startswith("--")]
    if cli_tasks:
        for t in cli_tasks:
            print(f"You: {t}")
            yield t
        return
    if not sys.stdin.isatty():
        for line in sys.stdin:
            t = line.strip()
            if t:
                print(f"You: {t}")
                yield t
        return
    while True:
        try:
            yield input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            return

# ─────────────────────────────────────────────────────────────────────────────
# Chat loop
# ─────────────────────────────────────────────────────────────────────────────
W = 76
print("=" * W)
if AUTO_MODE:
    print("  Buddy ready  |  AUTO mode  (fully autonomous: model, effort,")
    print("                 thinking, team, advisor & RAG routed per task;")
    print("                 self-healing escalation + live competency learning)")
else:
    print(f"  Buddy ready  |  {_sel_label.strip()}  (pinned)")
print(f"  Memory: buddy_memory.db   Sessions: buddy_sessions.db")
print(f"  Knowledge: buddy_knowledge.db   Metrics: buddy_metrics.db")
print(f"  Commands: /tools /models /model /status /metrics /eval /clear "
      f"/switch [id|auto] /advisor [on|off|auto] /rag [on|off|auto] exit")
print("=" * W)
print()

for user_input in _task_source():
    if not user_input:
        continue

    low = user_input.lower()

    if low in ("exit", "quit", "bye"):
        print("\n  Goodbye!\n")
        break

    if low == "/tools":
        print(f"\n  Loaded tools ({len(_loaded)}): {', '.join(_loaded)}\n")
        continue

    if low == "/model":
        m = MODEL_BY_ID.get(_sess.model_id)
        print(f"\n  Mode    : {'AUTO' if AUTO_MODE else 'fixed'}")
        print(f"  Model   : {m[0].strip() if m else _sess.model_id}")
        print(f"  ID      : {_sess.model_id}")
        print(f"  Runner  : {'Team' if _sess.is_team else 'Agent'}")
        print(f"  Effort  : {_sess.effort_level}")
        print(f"  Thinking: {_sess.thinking_mode}\n")
        continue

    if low == "/status":
        print(f"\n  Runner  : {'Team' if _sess.is_team else 'Agent'}")
        print(f"  Model   : {_sess.model_id}  ({_sess.prov})")
        print(f"  Effort  : {_sess.effort_level}   Thinking: {_sess.thinking_mode}")
        if _sess.analysis:
            print(f"  Advisor : {'ON' if _sess.analysis.get('needs_advisor') else 'OFF'}"
                  f"   RAG: {'ON' if _sess.analysis.get('needs_rag', True) else 'OFF'}"
                  f"   Domain: {_sess.analysis.get('domain', 'general')}"
                  f" ({_MON.tracker.get(_sess.analysis.get('domain', 'general')):.1f}/10)")
            print(f"  Rationale: {_sess.analysis.get('rationale', '')}")
        _kb_obj = _kb if _kb else None
        if _kb_obj:
            try:
                _info = _kb_obj.get_database_info() or {}
                print(f"  KB docs : {_info.get('total_documents', '?')}")
            except Exception:
                pass
        print(f"  Session : {_sess.session_id}")
        print(f"  Advisor : {'ON' if _sess._use_advisor else 'OFF'}")
        print(f"  Tools   : {len(_loaded)}\n")
        continue

    if low == "/clear":
        _sess.runner = None
        _sess.session_id = None
        _sess.analysis = {}
        if not AUTO_MODE:
            _sess.init_fixed()
        print("  Session cleared. New session will start on next message.\n")
        continue

    if low == "/models":
        _print_menu()
        continue

    if low.startswith("/advisor"):
        # /advisor            -> back to autonomous (meta-agent decides per task)
        # /advisor on|off     -> pin advisor state
        # /advisor auto       -> autonomous (default)
        arg = user_input.split(maxsplit=1)[1].strip().lower() if " " in user_input else "auto"
        if arg in ("on", "off"):
            _sess._use_advisor = (arg == "on")
            _sess.analysis = {}          # force rebuild on next auto-routing
            print(f"  Advisor pinned: {arg.upper()}\n")
            if not AUTO_MODE:
                _sess.init_fixed()
                print(f"  Agent rebuilt with advisor={arg.upper()}.\n")
        else:
            _sess.analysis = {}
            print("  Advisor: AUTO (meta-agent decides per task)\n")
        continue

    if low == "/metrics":
        _MON.summary()
        continue

    if low.startswith("/eval"):
        # /eval <expected answer>          -> LLM-as-judge accuracy (0-10) on the
        #                                     LAST answer (no re-run needed)
        # /eval reliability <tool1,tool2>  -> verify expected tool calls were made
        arg = user_input.split(maxsplit=1)[1].strip() if " " in user_input else ""
        rr  = getattr(_sess.runner, "run_response", None) if _sess.runner else None
        if rr is None or not getattr(rr, "content", None):
            print("  No previous run to evaluate — ask something first.\n")
            continue
        if arg.lower().startswith("reliability"):
            exp = [t.strip() for t in
                   arg[len("reliability"):].replace(",", " ").split() if t.strip()]
            if not exp:
                print("  Usage: /eval reliability <tool1,tool2,...>\n")
                continue
            try:
                from buddy.eval.reliability import ReliabilityEval
                ev  = ReliabilityEval(agent_response=rr, expected_tool_calls=exp)
                res = ev.run(print_results=True)
                ok  = bool(res and res.eval_status == "PASSED")
                _MON.tracker.record_outcome(
                    (_sess.analysis or {}).get("domain", "general"), ok, weight=0.5)
                print()
            except Exception as exc:
                print(f"  [Eval] reliability eval failed: {exc}\n")
        elif arg:
            try:
                from buddy.eval.accuracy import AccuracyEval
                _mrow  = MODEL_BY_ID.get(_META_ID) or MODEL_BY_ID["gpt-4o"]
                _judge = build_model(_mrow[2], _mrow[1], _mrow[3], _mrow[4],
                                     _mrow[5], _mrow[6], _mrow[7])
                ev = AccuracyEval(
                    input           = _last_task or "(unknown)",
                    expected_output = arg,
                    model           = _judge,
                )
                res = ev.run_with_output(output=str(rr.content),
                                         print_results=True, print_summary=False)
                if res and res.results:
                    score = res.results[-1].score
                    _MON.tracker.record_outcome(
                        (_sess.analysis or {}).get("domain", "general"),
                        score >= 7, weight=0.5)
                print()
            except Exception as exc:
                print(f"  [Eval] accuracy eval failed: {exc}\n")
        else:
            print("  Usage: /eval <expected answer>   or   "
                  "/eval reliability <tool1,tool2>\n")
        continue

    if low.startswith("/rag"):
        # /rag            -> autonomous (meta-agent decides per task)
        # /rag on|off     -> pin RAG state
        # /rag auto       -> autonomous (default)
        arg = user_input.split(maxsplit=1)[1].strip().lower() if " " in user_input else "auto"
        if arg in ("on", "off"):
            _rag_pin = (arg == "on")
            _sess.analysis = {}          # force rebuild on next auto-routing
            print(f"  RAG pinned: {arg.upper()}\n")
            if _rag_pin:
                _get_knowledge()         # kick off KB ingestion now
        else:
            _rag_pin = None
            _sess.analysis = {}
            print("  RAG: AUTO (meta-agent decides per task)\n")
        continue

    if low.startswith("/switch"):
        # /switch             -> AUTO mode (fully autonomous routing)
        # /switch auto        -> AUTO mode
        # /switch <model_id>  -> pin a specific model (no prompts)
        arg = user_input.split(maxsplit=1)[1].strip() if " " in user_input else "auto"
        if arg.lower() == "auto":
            AUTO_MODE = True
            _sess.runner   = None
            _sess.analysis = {}
            print("  Switched to AUTO mode — model routed autonomously per task.\n")
        elif arg in MODEL_BY_ID:
            (_sess.label, _sess.prov, _sess.model_id,
             _sess.ctx_k,  _sess.out_k, _sess.sup_effort,
             _sess.sup_thinking, _sess.is_reasoning,
             _sess.tier) = MODEL_BY_ID[arg]
            AUTO_MODE = False
            _sess.init_fixed()
            print(f"  Switched to: {_sess.model_id} (pinned)\n")
        else:
            print(f"  Unknown model '{arg}'. Use /models to list ids, "
                  f"or '/switch auto'.\n")
        continue

    _stream(user_input)