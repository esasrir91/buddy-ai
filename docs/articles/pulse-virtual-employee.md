# Meet PULSE: Your AI Teammate That Actually Works

Most AI tools wait for you to ask a question. **PULSE** is different — it is Buddy AI's **autonomous virtual employee**: a teammate with a name, a role, a task queue, and a memory that survives restarts. You onboard it like a new hire, teach it your systems, assign work, and it keeps going — including when you close the browser.

!!! note "Install Buddy AI"
    ```bash
    pip install buddy-ai[all]
    ```

    - **PyPI:** [buddy-ai](https://pypi.org/project/buddy-ai/)
    - **GitHub:** [esasrir91/buddy-ai](https://github.com/esasrir91/buddy-ai)
    - **Technical reference:** [PULSE docs](../advanced/pulse.md)

---

## Chatbot vs virtual employee

| | Typical chatbot | PULSE |
|---|-----------------|-------|
| **Trigger** | You send a prompt | Tasks sit in a queue; PULSE picks them up |
| **Output** | Text in a chat window | Real files (`.py`, `.md`, `.sql`, …) in a workspace |
| **Knowledge** | Whatever fits in context | KT from PDFs, URLs, and live sessions — retained permanently |
| **Continuity** | Often forgets between sessions | Long-term memory + conversation history across restarts |
| **Reporting** | None | Daily standups, activity feed, notifications |

PULSE is built for **doing work**, not just answering questions. The [Competency Engine](../advanced/competency.md) (new in v2.2.0) complements it by measuring *who* on your team is strongest in each domain — PULSE is the teammate that actually executes.

---

## What PULSE can do

Once you create an employee profile, PULSE operates as a persistent team member:

| Capability | What it means in practice |
|------------|---------------------------|
| **Identity** | Name, role, department, skills, timezone — PULSE introduces itself and behaves consistently |
| **Knowledge Transfer (KT)** | Learn from PDFs, documents, full website crawls (BFS, up to 20 pages), or **live** Socratic Q&A until ≥82% confidence |
| **Meetings** | Paste a transcript → summary, decisions, action items; PULSE's own items land on the Task Board |
| **Tasks** | Kanban board with autonomous execution — highest-priority todo picked up within ~30 seconds |
| **Chat** | Streaming conversation grounded in KT + long-term memory + recent history |
| **Knowledge Explorer** | Ask what PULSE knows about any topic it has been trained on |
| **Autonomous worker** | Background loop writes files, sends notifications, generates standups, suggests proactive tasks |

All employee data persists under `~/.pulse_data/` — profiles, KT sessions, tasks, memories, and workspace files survive server restarts.

!!! tip "Honest framing"
    PULSE is a **real autonomous agent layer** on top of an LLM — not magic. It needs a configured model and API key (or Ollama locally). Task quality depends on your prompts, KT depth, and the model you choose. It **creates files and manages a queue**; it does not replace code review, security audits, or human judgment on production changes.

---

## Start the web UI

One command launches the full dashboard:

```bash
buddy pulse start
# Opens http://localhost:8888
```

Useful flags:

```bash
buddy pulse start --port 3000 --no-browser   # custom port, no auto-open
buddy pulse start --host 0.0.0.0               # bind for LAN access
```

On first launch, the **onboarding wizard** walks you through creating your virtual employee. After that, nine sidebar pages cover day-to-day use:

| Page | Purpose |
|------|---------|
| **Dashboard** | Activity feed, current work, standup, proactive suggestions, knowledge domains |
| **KT Center** | Upload documents, crawl URLs, or start live KT sessions |
| **Meetings** | Process transcripts and extract action items |
| **Tasks** | Kanban board with auto/manual execution toggle |
| **Workspace** | Browse, view, and download files PULSE created |
| **Memory** | Long-term facts and conversation history — view, search, forget |
| **Chat** | Streaming WebSocket chat (KT + memory aware) |
| **Knowledge** | Explore what PULSE has learned across KT sessions |
| **Settings** | LLM provider, API key, auto-work toggle — no env vars required |

Configure your model under **Settings → AI Model & API Keys**. Supports OpenAI, Anthropic, Google, Groq, and Ollama — changes apply immediately.

The REST API is available at `http://localhost:8888/api/docs` while the server runs. See the [CLI reference](../cli/pulse.md) for `buddy pulse create`, `buddy pulse kt`, and `buddy pulse status`.

---

## Desktop app — PULSE that stays running

Closing a browser tab stops the web UI session. The **Buddy AI Desktop** app (`pulse-desktop/`) wraps the same PULSE stack in a native **Electron** shell for **Windows** and **macOS**:

- **System tray** — closing the window hides the app; the autonomous worker keeps running
- **Same dashboard** — loads `http://127.0.0.1:8888` served by `buddy pulse start`
- **Auto-start backend** — spawns `buddy pulse start --no-browser` on launch

### Prerequisites

1. Python 3.10+ with Buddy AI: `pip install buddy-ai[all]`
2. Built React UI (first time, from repo root):

```bash
cd pulse-ui
npm install
npm run build
```

3. Node.js 18+ for the desktop app

### Run in development

```bash
cd pulse-desktop
npm install
npm start
```

### Build installers

| Platform | Command | Output |
|----------|---------|--------|
| **Windows** | `npm run build:win` | `Buddy AI Setup *.exe` in `pulse-desktop/dist/` |
| **macOS** | `npm run build:mac` | `Buddy AI-*.dmg` in `pulse-desktop/dist/` |

```bash
cd pulse-desktop
npm install
npm run build:win   # Windows — run on a Windows PC
npm run build:mac   # macOS — must run on a Mac
```

!!! note "Installers need Python"
    Installers bundle the Electron shell. Users still need Python and `buddy-ai` installed (`pip install buddy-ai[all]`), unless you add a bundled Python sidecar later. Full details: [pulse-desktop/README.md](https://github.com/esasrir91/buddy-ai/blob/main/pulse-desktop/README.md).

**Windows tip:** If you hit symlink or code-signing errors during build:

```powershell
$env:CSC_IDENTITY_AUTO_DISCOVERY="false"
npm run build:win
```

Useful environment variables: `PULSE_PORT`, `BUDDY_PYTHON`, `PULSE_DATA_DIR`. See the [desktop README](https://github.com/esasrir91/buddy-ai/blob/main/pulse-desktop/README.md) for troubleshooting.

---

## Python API — quick start

Everything in the UI is also available programmatically. This example mirrors [`examples/11_pulse_employee.py`](https://github.com/esasrir91/buddy-ai/blob/main/examples/11_pulse_employee.py):

```python
import os

from buddy.models.openai import OpenAIChat
from buddy.pulse import EmployeeProfile, KTSourceType, PulseEmployee

if not os.getenv("OPENAI_API_KEY"):
    print("Set OPENAI_API_KEY to run this example.")
else:
    pulse = PulseEmployee(
        employee_profile=EmployeeProfile(
            full_name="Priya Sharma",
            role="Senior Backend Engineer",
            department="Engineering",
            skills=["Python", "FastAPI", "PostgreSQL"],
            timezone="Asia/Kolkata",
            company_name="Acme Corp",
        ),
        model=OpenAIChat(id="gpt-4o"),
    )

    print(pulse.introduce_yourself())

    # Document-based KT (text or file path)
    summary = pulse.take_kt(
        source=b"Our auth uses JWT with 1-hour expiry and Redis blocklist on logout.",
        source_type=KTSourceType.DOCUMENT,
        session_name="Auth Service Overview",
        knowledge_giver="Arjun Nair",
    )
    print(summary.format_summary())

    # Assign a task
    task = pulse.receive_task(
        title="Implement Razorpay refund flow",
        description="Handle refund_processed webhook events with idempotency.",
        assigned_by="Arjun Nair",
        priority="high",
    )
    print(task.format_brief())
```

For live KT, meetings, and status reports, see the [full PULSE reference](../advanced/pulse.md) or run the complete example script.

To launch the web server from Python:

```python
# from buddy.pulse.app import PulseApp
# PulseApp(employee=pulse).serve()
# Or simply: buddy pulse start
```

---

## What you need to know before you start

- **LLM API key required** for autonomous work, KT, chat, and meetings — configure in Settings or via `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.
- **Costs scale with usage** — the background worker polls every 30 seconds; each task, KT session, and chat turn calls your model.
- **Local data** — everything lives in `~/.pulse_data/`; back it up if employees matter to your workflow.
- **Ollama works** — run locally with no cloud key if you prefer, via Settings or a local Ollama instance.
- **Not a substitute for review** — PULSE generates real files; treat output like any junior engineer's PR.

---

## Next steps

- [PULSE — Virtual Employee (full reference)](../advanced/pulse.md) — API, REST endpoints, architecture
- [PULSE CLI commands](../cli/pulse.md) — `start`, `create`, `kt`, `status`
- [Example script](https://github.com/esasrir91/buddy-ai/blob/main/examples/11_pulse_employee.py) — runnable walkthrough
- [Desktop app README](https://github.com/esasrir91/buddy-ai/blob/main/pulse-desktop/README.md) — build, tray, troubleshooting
- [Teaching AI Agents to Know What They Don't Know](competency-engine-v2.2.0.md) — v2.2.0 Competency Engine (pairs with PULSE for routing)

```bash
pip install buddy-ai[all]
buddy pulse start
```

Give PULSE a role, teach it your stack, add a task — and let your virtual teammate get to work.
