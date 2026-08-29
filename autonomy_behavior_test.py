import ast, io, os, sys, typing

src = open("test.py", encoding="utf-8").read()
tree = ast.parse(src)

wanted = {"_resolve_boot_model", "_task_source", "_next_effort"}
funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
mod = ast.Module(body=funcs, type_ignores=[])
ns = {"os": os, "sys": sys, "Optional": typing.Optional,
      "MODEL_BY_ID": {"gpt-4o": None, "claude-fable-5": None, "gpt-5.6-sol": None},
      "_EFFORT_LADDER": ["low", "medium", "high", "xhigh", "max"]}
exec(compile(ast.fix_missing_locations(mod), "test_extract", "exec"), ns)

results = []
def check(name, cond):
    results.append((name, cond)); print(f"  {'PASS' if cond else 'FAIL'}  {name}")

orig_argv, orig_env = sys.argv[:], os.environ.get("BUDDY_MODEL")

# ── boot resolver ────────────────────────────────────────────────────
sys.argv = ["test.py"]; os.environ.pop("BUDDY_MODEL", None)
check("default boot -> AUTO (None)", ns["_resolve_boot_model"]() is None)
sys.argv = ["test.py", "--model=claude-fable-5"]
check("--model pins model", ns["_resolve_boot_model"]() == "claude-fable-5")
sys.argv = ["test.py", "--model=bogus"]
check("unknown --model -> AUTO", ns["_resolve_boot_model"]() is None)
sys.argv = ["test.py"]; os.environ["BUDDY_MODEL"] = "gpt-5.6-sol"
check("BUDDY_MODEL env pins model", ns["_resolve_boot_model"]() == "gpt-5.6-sol")
os.environ["BUDDY_MODEL"] = "auto"
check("BUDDY_MODEL=auto -> AUTO", ns["_resolve_boot_model"]() is None)

# ── task sources ─────────────────────────────────────────────────────
os.environ.pop("BUDDY_MODEL", None)
sys.argv = ["test.py", "--model=auto", "task one", "task two"]
check("CLI args become tasks (flags excluded)", list(ns["_task_source"]()) == ["task one", "task two"])
sys.argv = ["test.py"]
fake = io.StringIO("piped A\n\npiped B\n"); fake.isatty = lambda: False
real, sys.stdin = sys.stdin, fake
tasks = list(ns["_task_source"]()); sys.stdin = real
check("piped stdin headless (blanks skipped)", tasks == ["piped A", "piped B"])

# ── NEW: effort escalation ladder ────────────────────────────────────
ne = ns["_next_effort"]
check("low -> medium",   ne("low")    == "medium")
check("medium -> high",  ne("medium") == "high")
check("high -> xhigh",   ne("high")   == "xhigh")
check("xhigh -> max",    ne("xhigh")  == "max")
check("max -> None (ceiling)", ne("max") is None)
check("unknown -> 'high' fallback", ne("weird") == "high")

# ── NEW: live iRAG knowledge base ────────────────────────────────────
try:
    from buddy.knowledge import irag
    kb = irag(dir_path=os.getcwd(), formats=[".md", ".txt"],
              db_path="buddy_knowledge_test.db")
    check("irag KB instantiates (local, no embedding API)", True)
    check("irag exposes agentic search()", callable(getattr(kb, "search", None)))
    check("irag exposes load()", callable(getattr(kb, "load", None)))
finally:
    try: os.remove("buddy_knowledge_test.db")
    except OSError: pass

# ── NEW: live _Monitor + CompetencyTracker (real buddy.eval class) ──
import sqlite3, time, types
cls_node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "_Monitor")
mon_mod  = ast.Module(body=[cls_node], type_ignores=[])
from buddy.eval.competency_runtime import CompetencyTracker
mns = {"sqlite3": sqlite3, "time": time, "CompetencyTracker": CompetencyTracker,
       "_next_effort": ns["_next_effort"], "print": print}
exec(compile(ast.fix_missing_locations(mon_mod), "mon_extract", "exec"), mns)

db = "buddy_metrics_test.db"
try:
    if os.path.exists(db): os.remove(db)
    mon = mns["_Monitor"](db_path=db)

    class FakeRR:
        metrics = {"input_tokens": [100, 50], "output_tokens": [20, 30]}
        tools   = [{"tool_name": "search", "tool_call_error": None},
                   {"tool_name": "fetch",  "tool_call_error": "boom"}]
    class FakeRunner: run_response = FakeRR()
    class FakeSess:
        runner = FakeRunner(); model_id = "gpt-4o"; effort_level = "high"
        thinking_mode = "adaptive"; is_team = False; _use_advisor = False

    dec = {"domain": "coding", "needs_rag": True, "effort": "high"}
    mon.record("test task", FakeSess(), dec, 1.23, "ok")
    con = sqlite3.connect(db)
    row = con.execute("SELECT input_tokens, output_tokens, tool_calls, "
                      "tool_errors, status, domain FROM runs").fetchone()
    check("monitor records run row", row == (150, 50, 2, 1, "ok", "coding"))
    comp = con.execute("SELECT domain, observations FROM competency").fetchone()
    con.close()
    check("competency persisted to db", comp == ("coding", 1))
    # tool error -> outcome counted as failure -> score dropped below default 5.0
    check("tool error lowers competency (EMA)", mon.tracker.get("coding") < 5.0)

    # EMA math: two more failures -> below boost threshold (4.0) with >=3 obs
    mon.tracker.record_outcome("coding", False)
    mon.tracker.record_outcome("coding", False)
    d2 = {"domain": "coding", "effort": "high"}
    mon.competency_boost(d2)
    check("weak domain triggers autonomous effort boost", d2["effort"] == "xhigh")

    d3 = {"domain": "fresh", "effort": "high"}
    mon.competency_boost(d3)
    check("no boost without >=3 observations", d3["effort"] == "high")

    # persistence: new monitor reseeds tracker from disk
    mon2 = mns["_Monitor"](db_path=db)
    check("competency reseeds across sessions", mon2.tracker.get("coding") < 5.0)
finally:
    try: os.remove(db)
    except OSError: pass

# ── NEW: build_model with first-class models/ configs (live constructors) ──
from buddy.models.openai import OpenAIChat
from buddy.models.anthropic import Claude
from buddy.models.token_budget import TokenBudgetConfig
from buddy.models.effort import EffortConfig
from buddy.models.thinking import ThinkingConfig
from buddy.models.multilingual import MultilingualConfig
from buddy.models.cache import PromptCacheConfig
from buddy.models.fast_mode import FastModeConfig

bm_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_model")
bns = {"OpenAIChat": OpenAIChat, "Claude": Claude, "TokenBudgetConfig": TokenBudgetConfig,
       "EffortConfig": EffortConfig, "ThinkingConfig": ThinkingConfig,
       "MultilingualConfig": MultilingualConfig, "PromptCacheConfig": PromptCacheConfig,
       "FastModeConfig": FastModeConfig, "Optional": typing.Optional, "print": lambda *a, **k: None}
exec(compile(ast.fix_missing_locations(ast.Module(body=[bm_node], type_ignores=[])),
             "bm_extract", "exec"), bns)
bm = bns["build_model"]

m1 = bm("claude-fable-5", "ant", 200, 128, True, True, False, "high", "adaptive")
check("Claude gets first-class EffortConfig", isinstance(m1.effort, EffortConfig) and m1.effort.level == "high")
check("Claude gets validated ThinkingConfig", isinstance(m1.thinking_config, ThinkingConfig) and m1.thinking_config.mode == "adaptive")
check("Claude gets PromptCacheConfig (sys+tools+history)",
      isinstance(m1.prompt_cache_config, PromptCacheConfig) and m1.prompt_cache_config.cache_tools)
check("Claude refusal fallback wired", m1.refusal_fallback_model == "claude-sonnet-5")
check("no fast mode at high effort", m1.fast_mode is None)
check("multilingual off for English (cache-friendly)", m1.multilingual is None)

m2 = bm("claude-opus-5", "ant", 200, 128, True, True, False, "low", "adaptive", language="ta")
check("fast mode auto-ON for low-effort Opus", isinstance(m2.fast_mode, FastModeConfig))
check("meta-detected language enforced natively",
      isinstance(m2.multilingual, MultilingualConfig) and m2.multilingual.language == "ta" and m2.multilingual.enforce)
check("sonnet fallback for opus", m2.refusal_fallback_model == "claude-sonnet-5")
# Regression: Claude 5 rejects temperature even when adaptive thinking is off.
m2_disabled = bm("claude-opus-5", "ant", 200, 128, True, True, False, "medium", "disabled")
check("Claude 5 + thinking disabled omits deprecated temperature",
      m2_disabled.temperature is None and "temperature" not in m2_disabled.get_request_params())
check("Claude 5 also omits top_p/top_k",
      "top_p" not in m2_disabled.get_request_params() and "top_k" not in m2_disabled.get_request_params())

# Claude 4.7+ also rejects sampling params (not just Claude 5).
m47 = bm("claude-opus-4-7", "ant", 200, 128, True, True, False, "medium", "disabled")
check("Claude 4.7 omits deprecated temperature",
      m47.temperature is None and "temperature" not in m47.get_request_params())

# Framework-level guard also blocks direct and late request_params injection.
m2_guard = Claude(id="claude-opus-5", temperature=0.7, top_p=0.9, top_k=40,
                  request_params={"temperature": 0.2, "top_p": 0.5})
m2_guard.request_params = {"temperature": 0.9, "top_k": 10}
rp_guard = m2_guard.get_request_params()
check("Claude adapter defensively strips deprecated sampling params",
      not any(k in rp_guard for k in ("temperature", "top_p", "top_k")))

# Thinking + temperature must never both be sent (even on older Claude).
m_think = Claude(id="claude-opus-4-6", temperature=0.7,
                 thinking={"type": "adaptive"})
check("Thinking active strips temperature on Claude 4.6",
      "temperature" not in m_think.get_request_params())

# Bedrock / dated / proxied IDs must also match.
check("Bedrock-style Claude 5 ID rejects temperature",
      not Claude.supports_sampling_params("anthropic.claude-opus-5-v1:0"))
check("OpenRouter-style Claude 5 ID rejects temperature",
      not Claude.supports_sampling_params("anthropic/claude-sonnet-5"))

m3 = bm("gpt-5.6-sol", "oai", 400, 128, False, False, True, "xhigh", "adaptive")
check("OAI reasoning: native reasoning_effort", m3.reasoning_effort == "high")
check("OAI reasoning: no EffortConfig (no double-apply)", m3.effort is None)
check("OAI reasoning: temperature omitted",
      "temperature" not in m3.get_request_params())

# Direct injection on reasoning models is also stripped.
m3_guard = OpenAIChat(id="o3", temperature=0.7, request_params={"temperature": 0.2})
check("OAI adapter strips temperature on o3",
      "temperature" not in m3_guard.get_request_params())

m4 = bm("gpt-4o", "oai", 128, 16, False, False, False, "low", "adaptive")
check("OAI non-reasoning: prompt-hint EffortConfig", isinstance(m4.effort, EffortConfig) and m4.effort.level == "low")
check("OAI gets PromptCacheConfig", isinstance(m4.prompt_cache_config, PromptCacheConfig))
check("OAI non-reasoning still allows temperature",
      m4.temperature == 0.7 and m4.get_request_params().get("temperature") == 0.7)

sys.argv = orig_argv
if orig_env is not None: os.environ["BUDDY_MODEL"] = orig_env

passed = sum(1 for _, ok in results if ok)
summary = f"{passed}/{len(results)} behavioral tests passed"
print("\n" + summary)