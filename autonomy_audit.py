import ast

src = open("test.py", encoding="utf-8").read()
tree = ast.parse(src)

results = {}

# 1) input() calls must only exist inside _task_source (TTY fallback)
input_scopes = []
class Scope(ast.NodeVisitor):
    def __init__(self): self.stack = ["<module>"]
    def visit_FunctionDef(self, node):
        self.stack.append(node.name); self.generic_visit(node); self.stack.pop()
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == "input":
            input_scopes.append(self.stack[-1])
        self.generic_visit(node)
Scope().visit(tree)
results["input_only_in_tty_fallback"] = input_scopes == ["_task_source"]

# ── Boot / routing autonomy (from previous upgrade) ─────────────────
results["autonomous_boot"]   = "_resolve_boot_model" in src and "AUTO_MODE = _boot_model_id is None" in src
results["per_task_routing"]  = ("if AUTO_MODE:\n        _sess.init_auto(user_input)" in src
                                and "AUTO_MODE and _sess.runner is None" not in src)
results["advisor_autonomous"]= 'self._use_advisor  = bool(dec.get("needs_advisor", False))' in src
results["switch_no_prompt"]  = '/switch' in src and 'raw2 = input' not in src
results["headless_cli_args"] = "cli_tasks = [a for a in sys.argv[1:]" in src
results["headless_stdin"]    = "sys.stdin.isatty()" in src
results["switch_signature"]  = "_config_signature" in src

# ── NEW: Agentic RAG ─────────────────────────────────────────────────
results["rag_local_irag_kb"]     = "from buddy.knowledge import irag" in src
results["rag_lazy_singleton"]    = "def _get_knowledge()" in src
results["rag_background_ingest"] = "threading.Thread(target=_load, daemon=True)" in src
results["rag_agentic_search"]    = "search_knowledge=bool(knowledge_cfg)" in src
results["rag_agentic_update"]    = "update_knowledge=bool(knowledge_cfg)" in src
results["rag_meta_routed"]       = ("needs_rag" in src
                                    and 'use_rag      = bool(dec.get("needs_rag", True))' in src)
results["rag_in_signature"]      = 'bool(dec.get("needs_rag", True)),' in src
results["rag_pin_command"]       = '_rag_pin' in src and 'low.startswith("/rag")' in src

# ── NEW: Autonomous tool selection + caching ─────────────────────────
results["auto_tool_selection"]   = "auto_tool_selection=True" in src
results["prompt_caching"]        = "cache_prompt=True" in src

# ── NEW: Self-healing effort escalation ──────────────────────────────
results["effort_ladder"]         = '_EFFORT_LADDER = ["low", "medium", "high", "xhigh", "max"]' in src
results["effort_next_fn"]        = "def _next_effort" in src
results["auto_heal_rebuild"]     = "def _escalate_and_rebuild" in src
results["stream_retry_wrapper"]  = "_stream_once(user_input)" in src and "max_attempts" in src
results["heal_preserves_session"]= "session_id   = _sess.session_id" in src

# ── NEW: Monitoring & evaluation ─────────────────────────────────────
results["monitor_class"]         = "class _Monitor" in src
results["monitor_sqlite_runs"]   = "CREATE TABLE IF NOT EXISTS runs(" in src
results["monitor_competency_db"] = "CREATE TABLE IF NOT EXISTS competency(" in src
results["monitor_records_every_run"] = src.count("_MON.record(") >= 3
results["monitor_reliability_autocheck"] = "tool_call_error" in src
results["competency_tracker_wired"] = "from buddy.eval.competency_runtime import CompetencyTracker" in src
results["competency_feedback_loop"] = ("_MON.competency_boost(dec)" in src
                                       and 'dec["effort"] = nxt' in src)
results["competency_persisted"]  = "seed=seed or None" in src
results["domain_in_routing"]     = '"domain":     "general"' in src and "domain: str = Field" in src
results["metrics_command"]       = 'low == "/metrics"' in src and "def summary" in src
results["eval_accuracy_cmd"]     = ("from buddy.eval.accuracy import AccuracyEval" in src
                                    and "run_with_output" in src)
results["eval_reliability_cmd"]  = "from buddy.eval.reliability import ReliabilityEval" in src
results["eval_feeds_competency"] = src.count("_MON.tracker.record_outcome(") >= 2
results["escalations_counted"]   = "_MON.escalations_this_run += 1" in src
results["debug_flag_passthrough"]= 'os.environ["BUDDY_DEBUG"] = "true"' in src

# ── NEW: models/ folder first-class configs ──────────────────────────
results["effort_config_firstclass"]  = ("from buddy.models.effort import EffortConfig" in src
                                        and "EffortConfig(level=effort_level" in src
                                        and 'rp["output_config"]' not in src)
results["thinking_config_firstclass"]= ("from buddy.models.thinking import ThinkingConfig" in src
                                        and 'ThinkingConfig(' in src
                                        and 'kwargs["thinking"] = {"type"' not in src)
results["prompt_cache_config"]       = ("from buddy.models.cache import PromptCacheConfig" in src
                                        and "cache_history_mode=\"auto\"" in src)
results["fast_mode_autonomous"]      = ("from buddy.models.fast_mode import FastModeConfig" in src
                                        and '_fast.is_supported(model_id)' in src
                                        and 'effort_level in ("low", "medium")' in src)
results["multilingual_meta_routed"]  = ("from buddy.models.multilingual import MultilingualConfig" in src
                                        and "language: str = Field" in src
                                        and 'language     = dec.get("language", "en")' in src)
results["refusal_fallback"]          = ('refusal_fallback_model' in src
                                        and 'handle_streaming_refusals' in src)
results["no_effort_double_apply"]    = "if not is_reasoning:" in src
results["language_in_signature"]     = '(dec.get("language") or "en").lower(),' in src

# ── Preserved core features ──────────────────────────────────────────
for feat, needle in {
    "compaction":        "auto_compact(",
    "context_editing":   "moderate_editing()",
    "memory":            "SqliteMemoryDb(",
    "agentic_memory":    "enable_agentic_memory=True",
    "session_storage":   "SqliteAgentStorage(",
    "token_budget":      "TokenBudgetConfig",
    "team_formation":    "build_team(",
    "structured_routing":"response_model=RoutingDecision",
    "retries_backoff":   "exponential_backoff=True",
}.items():
    results[f"preserved_{feat}"] = needle in src

passed = sum(1 for v in results.values() if v is True)
total  = len(results)
print(f"AUTONOMY AUDIT v2: {passed}/{total} checks passed\n")
for k, v in results.items():
    print(f"  {'PASS' if v else 'FAIL'}  {k}")

audit_result = f"{passed}/{total} passed"