# Changelog

All notable changes to **buddy-ai** are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [2.2.0] — 2026-06-17

### Added
- **Competency Engine (`buddy.eval.competency`)** — a balance-aware competency score for agents and teams. Decomposes integrated competency into a *vertical* (per-domain depth), *crosswise* (dependency-weighted cross-domain interaction), and *deficit* (gap from a target base) component, and exposes a normalized competency index plus per-domain deficit, centrality, and priority.
  - `CompetencyEval` / `CompetencyResult` — score, breakdown, and rich summary/table output (consistent with the accuracy/reliability/performance evals).
  - `DeficitDrivenController` — turns per-domain priorities into ranked learning recommendations.
  - `AutonomousCompetencyLoop` — a background loop that reads live signals, scores competency, and automatically enqueues training jobs for the highest-priority gaps until a target index is reached.
- **Closed-loop training hook** — `TrainingJobManager.enqueue_from_competency()` starts fine-tuning jobs for the weakest domains, connecting the score to the existing training pipeline.
- **Runtime competency routing (`buddy.eval.competency_runtime`)** — applies the same signal at task-execution time:
  - `CompetencyTracker` — live per-domain competency updated from task outcomes via EMA; its `signal()` callables feed straight back into the autonomous loop.
  - `LLMDomainClassifier` (with keyword fallback) — infers a task's domain.
  - `CompetencyRouter` — routes each task to the most competent member, selects an execution policy (proceed / review / escalate) and model tier (standard / strong), and records the outcome back into the tracker.
- **`EvalType.COMPETENCY`** — competency runs are recorded through the existing eval logging path.
- **LangChain & LangGraph integrations (`buddy.integrations`)** — optional, dependency-light adapters with lazy imports:
  - LangChain: `BuddyChatModel` (any Buddy model as a `BaseChatModel`), `BuddyAgentTool` (a Buddy agent/team as a LangChain tool), `to_langchain_tool` / `from_langchain_tool`, and `to_buddy_messages` / `from_buddy_message`.
  - LangGraph: `BuddyNode` (Buddy agent/team as a graph node), `add_buddy_node`, `build_sequential_graph`, `build_default_state`, and `make_competency_edge` (Competency Engine routing as a conditional edge).
  - `buddy.LANGCHAIN_AVAILABLE` / `buddy.LANGGRAPH_AVAILABLE` flags, new `[langchain]` and `[langgraph]` extras.
- **Docs & examples** — new `docs/advanced/competency.md`, `docs/integrations/` pages, `examples/12_competency_engine.py`, and `examples/13_langchain_langgraph.py`.

### Notes
- The competency index is an interpretable aggregation/orchestration layer; it does not by itself change model capability. With a non-trivial domain-dependency graph the crosswise term becomes a genuine, non-separable interaction signal.

---

## [2.1.3] — 2026-06-14

### Fixed
- **Seamless employee recovery** — `EmployeeValidator` now silently re-registers the employee from `lastKnownProfile` (persisted in localStorage) instead of dropping to onboarding when the server restarts; the onboarding wizard is shown only on first-ever use
- **`lastKnownProfile`** added to Zustand store — survives `clearEmployee()` so recovery is always possible even if the active session was cleared by older code

### Added
- **Full URL crawling for KT** — `KTSourceType.URL` now BFS-crawls the entire same-domain site (up to 20 pages, 3 link-hops deep, 30 k chars fed to LLM) instead of fetching a single page
- **KT knowledge injected into chat** — chat WebSocket endpoint now prepends all committed KT summaries to the prompt so PULSE can answer questions from its learned knowledge
- **Task completion notes** — moving a task to `done` triggers an AI-generated first-person completion note displayed directly on the Kanban card
- **Employee persistence** — employees are saved to `~/.pulse_data/employees.json` on create/update and restored automatically on server startup

### Changed
- Docs CI workflow: removed `--strict` flag and added `pip install buddy-ai` so the MkDocs build reliably deploys to GitHub Pages on every push
- Updated PULSE documentation to reflect all v2.1.x features

---

## [2.1.2] — 2026-06-14

### Fixed
- **PULSE Chat WebSocket flood loop** — `usePulseChat` hook now uses exponential backoff (max 5 retries) instead of infinite 300 ms retries; receiving a server error frame stops all reconnects immediately
- **Stale employee after server restart** — `EmployeeValidator` component checks the stored employee ID against the live server on every app load; if the server has restarted and lost state the app auto-redirects to onboarding instead of getting stuck
- Simplified `Chat.tsx` `handleSend` — removed dead code branch that called `sendMessage` twice

---

## [2.1.1] — 2026-06-14

### Changed
- Updated README with full PULSE documentation, feature overview, and improved PyPI project page

---

## [2.1.0] — 2026-06-14

### Summary
Introduces **PULSE — Virtual Employee's ERA**, the flagship new feature of buddy-ai.
PULSE turns any Buddy AI agent into a fully-functional virtual human team member
with a stable professional identity, interactive knowledge transfer, meeting intelligence,
task management, proactive communication, and a built-in web UI — all configurable
through a polished React dashboard with in-app LLM model and API key management.

### Added
- **`buddy/pulse/` module** — complete virtual employee system (12 Python files)
  - `PulseEmployee` — main class extending `Agent` with professional identity
  - `EmployeeProfile` — identity card: name, role, department, skills, timezone, communication style
  - `ColleagueBook` / `ColleagueRecord` — team directory
  - `WorkingHours` / `WorkStyle` — availability and personality configuration
  - `KTSession` / `KTManager` — 5-phase knowledge transfer engine supporting both async (document) and live (human-interactive) modes
  - `KTSourceType` — 11 source types: `DOCUMENT`, `URL`, `HUMAN_CHAT`, `HUMAN_VOICE_CALL`, and more
  - `KTSummary` / `KTTurn` — structured KT output with confidence scoring
  - `ProfessionalMemory` — composes Memory v2 with typed KT knowledge, colleague memory, decisions, and project context stores
  - `MeetingParticipant` / `MeetingNotes` — process transcripts, extract action items and decisions
  - `TranscriptProcessor` — parse raw meeting transcripts (timestamped or plain)
  - `TaskManager` / `WorkItem` / `WorkCalendar` — full task management
  - `StatusUpdate` — standup-format status reports
  - `CommunicationHub` — unified Slack / Gmail / Teams / Zoom messaging
  - `FeedbackSystem` / `PerformanceTracker` / `GrowthMetrics` — feedback and growth engine
  - `OnboardingWorkflow` — automates first-day onboarding as a Workflow v1 subclass
- **`buddy/pulse/router.py`** — FastAPI REST + WebSocket endpoints (`/api/pulse/*`), including:
  - `GET/POST /api/pulse/settings/llm` — read and persist LLM provider, model, and API key (injected into server env)
  - `POST /api/pulse/settings/llm/test` — live connection test against the chosen model
- **`buddy/pulse/app.py`** — `PulseApp` serving the React UI + API in one command
- **`buddy/cli/pulse_cli.py`** — `buddy pulse` CLI sub-commands (`start`, `create`, `kt`, `status`)
- **`buddy pulse start`** registered in `buddy/cli/entrypoint.py`
- **`PULSE_AVAILABLE`** flag in `buddy/__init__.py` for feature-gated imports
- **`pulse-ui/`** — full React 18 + TypeScript + Vite + TailwindCSS web application
  - 9 pages: Onboarding Wizard, Dashboard, KT Center, Live KT Session, Meeting Room, Task Board, Chat, Knowledge Explorer, Settings
  - Live KT 3-panel layout: chat dialogue + real-time Confidence Meter + Mental Model panel
  - Settings page with full **AI Model & API Keys** section:
    - Provider tabs (OpenAI · Anthropic · Google · Groq · Ollama)
    - Per-provider model dropdown with curated presets + custom model ID entry
    - Masked API key input with show/hide toggle and key-rotation support
    - Base URL field for Ollama and custom OpenAI-compatible endpoints
    - "Test Connection" button — pings the model live and shows response
    - "Save & Apply" — persists to server env and re-wires all running employees instantly
  - Zustand store with localStorage persistence for employee session
  - WebSocket streaming chat hook
- **`examples/11_pulse_employee.py`** — runnable end-to-end PULSE example
- **`docs/advanced/pulse.md`** — comprehensive PULSE documentation
- **`tests/unit/test_pulse.py`** — 36 unit tests covering all PULSE modules (all passing)

### Fixed
- `ProfessionalMemory` refactored from inheriting `Memory` (plain Python class) to composing it, eliminating `AttributeError: 'FieldInfo' object has no attribute 'append'` on list fields

---

## [2.0.0] — 2026-06-14

### Summary
Major release establishing the engineering foundation for production-grade adoption.
Fixes all critical bugs, completes the planning module, adds proper testing infrastructure,
Docker support, full documentation, and a comprehensive examples library.

### Fixed
- **Version inconsistency** — `pyproject.toml`, `buddy/__init__.py`, and CLI now all report the same version (`2.0.0`)
- **CLI `--version` flag** — `buddy --version` now correctly reads the installed `buddy-ai` package version instead of returning `"dev-local"`
- **`get_app_version()`** — now resolves against the correct PyPI package name `buddy-ai`
- **`MANIFEST.in`** — removed references to non-existent `*.html`, `*.css`, `*.js` playground assets that broke `pip install` package builds
- **Planning module** — `REACTIVE`, `DELIBERATIVE`, and `HYBRID` strategies were `None` stubs that raised `ValueError` at runtime; all three are now fully implemented (`ReactiveThinkPlanning`, `DeliberativePlanning`, `HybridPlanning`)

### Added
- **`[training]` optional extra** — `pip install buddy-ai[training]` now installs `torch`, `transformers`, `datasets`, `accelerate`, `peft`
- **`[multimodal]` optional extra** — `pip install buddy-ai[multimodal]` now installs `Pillow`, `opencv-python`, `librosa`, `soundfile`
- **`[tools]` optional extra** — `pip install buddy-ai[tools]` installs common tool SDK dependencies
- **`pytest-cov`** added to `[dev]` extras and coverage config added to `pyproject.toml`
- **`[tool.pytest.ini_options]`** section in `pyproject.toml` for zero-config test runs
- **`tests/`** directory with unit tests covering `Agent`, `Team`, `Workflow`, `Planning`, `Memory`, and `Tools`
- **`.github/workflows/tests.yml`** — CI workflow running lint + type-check + pytest on every push/PR
- **`examples/`** directory with 10+ runnable scripts covering common use cases
- **`CONTRIBUTING.md`** — contribution guide for open-source contributors
- **`CODE_OF_CONDUCT.md`** — Contributor Covenant v2.1
- **`.env.example`** — complete reference of all supported environment variables
- **`Dockerfile`** + **`docker-compose.yml`** for containerised deployment
- Full **MkDocs documentation** filling all 100+ pages declared in `mkdocs.yml`

### Changed
- `pyproject.toml` `[dev]` extras now include `pytest-cov`
- `HybridPlanning` replanning now inherits deliberative backbone and adds reactive fallback step

---

## [1.0.5] — 2025-12-01

### Added
- iRAG (intelligent RAG) with spaCy + TF-IDF + cosine similarity
- AG-UI compatible router
- 35+ model provider adapters
- Memory v2 with SQLite, Postgres, Redis, MongoDB, Firestore backends
- Workflow v2 engine with conditions, loops, parallel execution

### Fixed
- LanceDB async search compatibility
- Qdrant v2.0.0 migration helpers

---

## [1.0.0] — 2025-06-01

### Added
- Initial public release
- `Agent`, `Team`, `Workflow` core classes
- FastAPI and Playground servers
- Slack, Discord, WhatsApp channel integrations
- CLI (`buddy ws`, `buddy train`)
- 90+ built-in tools
- 14 vector database integrations
- Local model training pipeline

[2.1.3]: https://github.com/esasrir91/buddy-ai/compare/v2.1.2...v2.1.3
[2.1.2]: https://github.com/esasrir91/buddy-ai/compare/v2.1.1...v2.1.2
[2.1.1]: https://github.com/esasrir91/buddy-ai/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/esasrir91/buddy-ai/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/esasrir91/buddy-ai/compare/v1.0.5...v2.0.0
[1.0.5]: https://github.com/esasrir91/buddy-ai/compare/v1.0.0...v1.0.5
[1.0.0]: https://github.com/esasrir91/buddy-ai/releases/tag/v1.0.0
