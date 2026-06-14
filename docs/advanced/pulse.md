# PULSE — Autonomous Virtual Employee

**PULSE** is the flagship feature of buddy-ai v2.1. It is a fully autonomous virtual team member — not a chatbot you prompt, but an AI employee that works through your task queue, learns from your documents, attends your meetings, and reports back, all without being managed.

---

## Quick Start

```bash
pip install buddy-ai
buddy pulse start
# Opens http://localhost:8888
```

That's it. The web UI walks you through creating your virtual employee.

---

## What PULSE Does Autonomously

Once created, a PULSE employee operates independently:

| Behaviour | How |
|-----------|-----|
| **Works tasks** | Picks the highest-priority todo task, executes it using its KT knowledge, marks it done with full work output — every 30 seconds |
| **Sends notifications** | Notifies you every time it completes work with a summary of what it did |
| **Daily standup** | Generates a first-person standup report once per day — what it worked on, what's next, any observations |
| **Suggests tasks** | Proactively proposes 3 high-value tasks based on its role and knowledge — once per day |
| **Activity feed** | Logs every autonomous action with timestamp — visible live on the Dashboard |
| **Learns from documents** | Reads PDFs, crawls entire websites (BFS, up to 20 pages), and retains knowledge permanently |
| **Attends meetings** | Processes transcripts, extracts decisions and action items, creates tasks from its own action items |
| **Answers from knowledge** | Every chat response uses everything it has learned — KT sessions are injected as context |

---

## Web UI

```bash
buddy pulse start
buddy pulse start --port 3000 --no-browser
```

### Dashboard

The command centre for your virtual employee:

- **Activity Feed** — live log of every action PULSE takes (tasks started/done, KT learned, standups, suggestions)
- **Currently Working On** — shows in-progress tasks with a live pulsing indicator
- **Daily Standup** — generate on demand or let it auto-generate once per day
- **PULSE Suggests** — PULSE proposes proactive tasks based on its role and knowledge; add them with one click
- **Knowledge Domains** — all topics PULSE has been trained on

### Task Board

Kanban board with full autonomous execution:

- Add a task → PULSE picks it up within 30 seconds
- Blue pulsing dot on a card means PULSE is actively working on it
- When done, the full AI-generated work output appears in the card
- **Auto / Manual toggle** — disable auto-work if you want to control task execution yourself
- Board auto-refreshes every 15 seconds

### KT Center

Teach PULSE from any source:

- **Document / PDF** — upload or provide a file path; text is extracted with `pypdf`
- **URL** — PULSE crawls the entire website (BFS up to 20 pages, 3 hops deep, same domain)
- **Live KT** — real-time interactive session where PULSE asks Socratic questions until it reaches ≥82% confidence

### Meeting Room

Paste any meeting transcript. PULSE extracts:

- Summary
- Decisions made
- Action items with owners
- Its own action items are automatically added to the Task Board

### Chat

Streaming WebSocket conversation. Every response uses the full KT knowledge base as context — ask about any document it has read and it answers as a team member who was there.

### Notifications

Bell icon in the sidebar with unread count. PULSE sends you a notification for:

- Every task it completes (with work summary)
- Daily standup reports
- Proactive task suggestions

### Settings

Configure LLM model and API key directly in the UI — no environment variables needed. Supports:

- **OpenAI** — 22 models including GPT-4.1, GPT-4o, o3, o4-mini, o1
- **Anthropic** — Claude Opus, Sonnet, Haiku
- **Google** — Gemini 1.5 Pro, 2.0 Flash
- **Groq** — Llama 3.3, Mixtral
- **Ollama** — any local model

Changes apply immediately to all active employees.

---

## Python API

### Create an employee

```python
from buddy.pulse import PulseEmployee, EmployeeProfile, KTSourceType
from buddy.models.openai import OpenAIChat

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
```

### Knowledge Transfer

```python
# From a PDF
summary = pulse.take_kt(
    source="docs/payments_architecture.pdf",
    source_type=KTSourceType.DOCUMENT,
    session_name="Payments KT",
    knowledge_giver="Arjun Nair",
)

# From a URL (crawls the entire site)
summary = pulse.take_kt(
    source="https://docs.yourproduct.com",
    source_type=KTSourceType.URL,
    session_name="Product Docs KT",
    knowledge_giver="Docs Site",
)

print(f"Confidence: {summary.confidence_score:.0%}")
print(f"Mental model: {summary.mental_model}")
```

### Live KT (interactive)

```python
session = pulse.start_live_kt(
    session_name="Auth Service KT",
    knowledge_giver="Arjun Nair",
    source_type=KTSourceType.HUMAN_CHAT,
)

turn = session.human_explains("Our auth uses JWT with 1-hr expiry...")
print(turn.pulse_message)  # PULSE asks targeted questions

turn = session.human_answers({"Q1": "User must re-login", "Q2": "Yes, Redis blocklist"})
print(f"Confidence: {turn.confidence_score:.0%}")

summary = pulse.finalize_kt_session(session)
```

### Meetings

```python
from buddy.pulse import MeetingPlatform

notes = pulse.attend_meeting(
    transcript="Arjun: Complete the Razorpay migration by EOD. Priya: I'll take the refund flow.",
    participants=["Arjun Nair", "Priya Sharma"],
    platform=MeetingPlatform.ZOOM,
    title="Sprint Sync",
)

print(notes.format_summary())
# Action items assigned to PULSE are auto-added to its task list
```

### Tasks

```python
task = pulse.receive_task(
    title="Implement Razorpay refund flow",
    description="Handle refund_processed webhook events...",
    assigned_by="Arjun Nair",
    priority="high",
    deadline="2026-06-27",
)

task.start()
task.add_note("Reviewed Razorpay refund webhook docs")

update = pulse.report_status(task_id=task.task_id)
print(update.format_standup())
```

---

## Data Persistence

All employee data is saved to `~/.pulse_data/employees.json` on every change:

- Employee profile
- All KT session summaries and mental models
- Task list with statuses, notes, and work output
- LLM configuration

On `buddy pulse start`, everything is automatically restored — no re-onboarding needed.

---

## REST API Reference

When running `buddy pulse start`, the full API is available at `http://localhost:8888/api/docs`.

### Employee

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/pulse/employees` | Create a PULSE employee |
| `GET` | `/api/pulse/employees/{id}` | Get employee profile + status |
| `PUT` | `/api/pulse/employees/{id}` | Update employee profile |

### Knowledge Transfer

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/pulse/{id}/kt/async` | KT from document, PDF, or URL |
| `POST` | `/api/pulse/{id}/kt/live` | Start a live KT session |
| `POST` | `/api/pulse/{id}/kt/{sid}/explain` | Human explains a chunk |
| `POST` | `/api/pulse/{id}/kt/{sid}/answer` | Human answers questions |
| `POST` | `/api/pulse/{id}/kt/{sid}/commit` | Finalise the session |
| `GET` | `/api/pulse/{id}/kt` | List all KT sessions |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/pulse/{id}/tasks` | Assign a task |
| `GET` | `/api/pulse/{id}/tasks` | List all tasks |
| `PUT` | `/api/pulse/{id}/tasks/{tid}` | Update status or add a note |
| `GET` | `/api/pulse/{id}/tasks/{tid}/status-update` | Get AI status report |

### Meetings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/pulse/{id}/meetings` | Process a meeting transcript |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/pulse/{id}/chat` | Single-turn chat (KT-aware) |
| `WS` | `/api/pulse/{id}/chat/stream` | Streaming WebSocket chat |

### Activity & Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/pulse/{id}/activity` | Get activity log |
| `GET` | `/api/pulse/{id}/notifications` | Get notifications with unread count |
| `POST` | `/api/pulse/{id}/notifications/read-all` | Mark all as read |

### Standup & Suggestions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/pulse/{id}/standup` | Generate daily standup |
| `POST` | `/api/pulse/{id}/suggest-tasks` | Get proactive task suggestions |

### Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/pulse/settings/llm` | Get LLM configuration |
| `POST` | `/api/pulse/settings/llm` | Save LLM configuration |
| `POST` | `/api/pulse/settings/llm/test` | Test LLM connection |
| `GET` | `/api/pulse/settings/auto-work` | Get auto-work status |
| `POST` | `/api/pulse/settings/auto-work` | Enable / disable auto-work |

---

## Architecture

```
buddy/pulse/
├── employee.py      # PulseEmployee (extends Agent)
├── identity.py      # EmployeeProfile, WorkingHours, WorkStyle
├── kt.py            # KTSession, KTManager, KTSourceType, KTSummary — includes PDF + URL crawler
├── meeting.py       # MeetingParticipant, MeetingNotes, ActionItem, TranscriptProcessor
├── work.py          # WorkItem, TaskManager, WorkCalendar, StatusUpdate
├── comms.py         # CommunicationHub (Slack, Gmail, Teams, Zoom)
├── memory.py        # ProfessionalMemory
├── onboarding.py    # OnboardingWorkflow
├── feedback.py      # FeedbackSystem, PerformanceTracker
├── router.py        # FastAPI endpoints + autonomous background worker
├── app.py           # PulseApp (serves React UI + API, starts auto worker on startup)
└── __init__.py      # Public exports
```

The **autonomous background worker** runs inside the FastAPI event loop:

1. Every 30 seconds, checks each employee's todo queue
2. Picks the highest-priority task, runs it through the LLM (in a thread pool, non-blocking)
3. Stores the full work output in the task's `progress_notes`
4. Sends a notification and logs the event to the activity feed
5. Once the queue is empty, generates the daily standup (once per day)
6. Suggests proactive tasks (once per day)

---

## CLI

```bash
# Start the server
buddy pulse start
buddy pulse start --port 3000 --no-browser

# Create an employee config interactively
buddy pulse create --name "Priya Sharma" --role "Backend Engineer"

# Run a KT session from the CLI
buddy pulse kt docs/architecture.pdf --session "Architecture KT" --from "Arjun"

# Check module status
buddy pulse status
```
