# PULSE — Virtual Employee's ERA

**PULSE** is the flagship feature of Buddy AI v2.1. It turns any Buddy AI `Agent` into a fully-functional **virtual human team member** that can take KTs, attend meetings, manage tasks, communicate proactively, and grow over time — just like a real employee.

---

## What PULSE Is

A `PulseEmployee` is an AI agent that:

- **Has an identity** — name, role, department, skills, timezone, communication style
- **Learns from knowledge transfer (KT)** — reads documents *and* takes live KT sessions from human colleagues
- **Attends meetings** — processes transcripts, extracts action items and decisions
- **Manages work** — receives tasks, tracks progress, reports blockers
- **Communicates proactively** — sends EOD summaries, asks for clarification, updates teammates
- **Grows over time** — receives feedback, improves behaviour, tracks performance

---

## Quick Start

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

---

## Core Concepts

### 1. Identity Layer

`EmployeeProfile` is the identity card of a PULSE employee. It shapes:
- The system prompt injected into the agent
- Introduction messages
- Communication style
- Working hours and availability

```python
from buddy.pulse import EmployeeProfile, WorkingHours, WorkStyle, CommunicationStyle

profile = EmployeeProfile(
    full_name="Alex Chen",
    role="Data Scientist",
    department="Data",
    team="ML Platform",
    reporting_to="Sarah Kim",
    skills=["Python", "PyTorch", "SQL"],
    domain_expertise=["recommendation systems", "fraud detection"],
    timezone="US/Pacific",
    work_mode="remote",
    working_hours=WorkingHours.standard_five_day(),
    work_style=WorkStyle(
        communication_style=CommunicationStyle.CONCISE,
        asks_clarifying_questions=True,
        proactively_shares_updates=True,
    ),
    company_name="TechCorp",
    bio="ML engineer focused on production model serving.",
)
```

---

### 2. Knowledge Transfer (KT)

PULSE can learn from both **documents** (async mode) and **humans** (live interactive mode).

#### Document / URL KT (async)

```python
summary = pulse.take_kt(
    source="docs/payments_system_overview.pdf",
    source_type=KTSourceType.DOCUMENT,
    session_name="Payments Architecture KT",
    knowledge_giver="Arjun Nair",
)

print(f"Confidence: {summary.confidence_score:.0%}")
print(f"Mental model: {summary.mental_model}")
print(f"Open questions: {summary.open_questions}")
```

Supported async source types:

| `KTSourceType` | Description |
|---|---|
| `DOCUMENT` | PDF, text file, or raw bytes |
| `URL` | Web page or online document |
| `AUDIO_TRANSCRIPT` | Transcript from audio recording |
| `VIDEO_TRANSCRIPT` | Transcript from screen recording |
| `WIKI_PAGE` | Confluence / Notion page |
| `MEETING_RECORDING` | Past meeting transcript |
| `CODEBASE` | Source code or repo summary |

#### Live / Human KT (interactive)

PULSE drives a Socratic dialogue until it reaches ≥82% confidence:

```python
session = pulse.start_live_kt(
    session_name="Auth Service KT",
    knowledge_giver="Arjun Nair",
    source_type=KTSourceType.HUMAN_CHAT,
)

# Human explains
turn = session.human_explains("Our auth uses JWT tokens with 1-hr expiry...")
print(turn.pulse_message)
# → "Thanks! I have 2 questions:
#    1. What happens when a refresh token expires?
#    2. Are tokens blocklisted on logout?"

# Human answers
turn = session.human_answers({
    "Q1": "User must re-login",
    "Q2": "Yes, Redis blocklist",
})
print(f"Confidence now: {turn.confidence_score:.0%}")

# Optional: correct something
session.human_corrects("Tokens are also rotated on every refresh.")

# Finalize
summary = pulse.finalize_kt_session(session)
print(summary.format_summary())
```

The `KTSession` object exposes:

| Method | Description |
|---|---|
| `human_explains(text)` | Human explains a chunk → returns `KTTurn` |
| `human_answers(answers)` | Human answers PULSE's questions → returns `KTTurn` |
| `human_corrects(correction)` | Human corrects PULSE's understanding |
| `generate_summary()` | Produce the final `KTSummary` |
| `commit()` | Mark the session as complete |

---

### 3. Meeting Intelligence

```python
from buddy.pulse import MeetingPlatform

notes = pulse.attend_meeting(
    transcript="""
    Arjun: We need to complete the Razorpay migration by end of June.
    Priya: I'll take the refund flow as an action item.
    Dev: I'll handle the integration tests.
    """,
    participants=["Arjun Nair", "Priya Sharma", "Dev"],
    platform=MeetingPlatform.ZOOM,
    title="Razorpay Migration Sync",
)

print(notes.format_summary())
for action in notes.action_items:
    print(f"[{action.owner}] {action.description}")
```

Meeting action items assigned to the PULSE employee are **automatically added to their task list**.

---

### 4. Task Management

```python
task = pulse.receive_task(
    title="Implement Razorpay refund flow",
    description="Handle refund_processed webhook events...",
    assigned_by="Arjun Nair",
    priority="high",
    deadline="2026-06-27",
    tags=["payments", "razorpay"],
)

task.start()
task.add_note("Reviewed Razorpay refund webhook docs")

# Get a status update
update = pulse.report_status(task_id=task.task_id)
print(update.format_standup())
```

---

### 5. Knowledge Introspection

```python
# Ask PULSE what it knows about a topic
knowledge = pulse.what_do_i_know_about("authentication tokens")
print(knowledge)
```

---

### 6. Feedback & Growth

```python
pulse.receive_feedback(
    content="Your status updates are really clear and timely.",
    given_by="Arjun Nair",
    category="communication",
    sentiment="positive",
)

pulse.receive_feedback(
    content="Please be more concise when summarising meeting notes.",
    given_by="Sarah Kim",
    category="communication",
    sentiment="constructive",
)
```

Constructive feedback is automatically incorporated into PULSE's system prompt so it improves over time.

---

### 7. Onboarding

```python
result = pulse.run_onboarding(
    company_docs=["docs/architecture.pdf", "docs/runbook.md"],
    team_members=[
        {"name": "Arjun Nair", "role": "Tech Lead"},
        {"name": "Sarah Kim", "role": "Product Manager"},
    ],
)
print(result["introduction"])
```

Or with the full `OnboardingWorkflow`:

```python
from buddy.pulse import OnboardingWorkflow, OnboardingConfig
from buddy.pulse.identity import ColleagueRecord

workflow = OnboardingWorkflow(employee=pulse)
config = OnboardingConfig(
    company_name="Acme Corp",
    company_docs=["docs/architecture.pdf"],
    team_members=[ColleagueRecord(full_name="Arjun Nair", role="Tech Lead")],
    introduction_channel="general",
    send_introduction_to="general",
)
for chunk in workflow.run(config):
    print(chunk.content, end="", flush=True)
```

---

## Web UI

PULSE comes with a built-in web interface. One command starts everything:

```bash
buddy pulse start
# Opens http://localhost:8888
```

Or from Python:

```python
from buddy.pulse.app import PulseApp
PulseApp().serve()
```

The UI provides:
- **Onboarding Wizard** — set up a PULSE employee without writing code
- **Dashboard** — today's tasks, meetings, and activity feed
- **KT Center** — manage async and live KT sessions
- **Live KT Chat** — real-time interactive KT dialogue with confidence meter
- **Meeting Room** — process meeting transcripts and review action items
- **Task Board** — Kanban-style task management
- **Chat** — direct conversation with the PULSE employee
- **Knowledge Explorer** — search and browse what PULSE knows
- **Settings** — profile, integrations, storage configuration

---

## CLI

```bash
# Start the web server
buddy pulse start
buddy pulse start --port 3000 --no-browser

# Create an employee config interactively
buddy pulse create --name "Priya Sharma" --role "Backend Engineer"

# Run a KT session from the CLI
buddy pulse kt docs/architecture.pdf --session "Architecture KT" --from "Arjun"

# Check PULSE module status
buddy pulse status
```

---

## Architecture

```
buddy/pulse/
├── employee.py      # PulseEmployee (extends Agent)
├── identity.py      # EmployeeProfile, ColleagueBook, WorkingHours, WorkStyle
├── kt.py            # KTSession, KTManager, KTSourceType, KTSummary, KTTurn
├── meeting.py       # MeetingParticipant, MeetingNotes, ActionItem, TranscriptProcessor
├── work.py          # WorkItem, TaskManager, WorkCalendar, StatusUpdate
├── comms.py         # CommunicationHub (Slack, Gmail, Teams, Zoom)
├── memory.py        # ProfessionalMemory (extends Memory v2)
├── onboarding.py    # OnboardingWorkflow (extends Workflow v1)
├── feedback.py      # FeedbackSystem, PerformanceTracker, GrowthMetrics
├── router.py        # FastAPI REST + WebSocket endpoints
├── app.py           # PulseApp (serves React UI + API)
└── __init__.py      # Public exports
```

---

## REST API

When running `buddy pulse start`, the following endpoints are available:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/pulse/employees` | Create a PULSE employee |
| `GET` | `/api/pulse/employees/{id}` | Get employee profile + status |
| `POST` | `/api/pulse/{id}/kt/async` | Run a document KT |
| `POST` | `/api/pulse/{id}/kt/live` | Start a live KT session |
| `POST` | `/api/pulse/{id}/kt/{sid}/explain` | Human explains a chunk |
| `POST` | `/api/pulse/{id}/kt/{sid}/answer` | Human answers questions |
| `POST` | `/api/pulse/{id}/kt/{sid}/commit` | Finalise a live KT |
| `POST` | `/api/pulse/{id}/meetings` | Process a meeting transcript |
| `POST` | `/api/pulse/{id}/tasks` | Assign a task |
| `POST` | `/api/pulse/{id}/chat` | Single-turn chat |
| `WS` | `/api/pulse/{id}/chat/stream` | Streaming WebSocket chat |
| `GET` | `/api/pulse/{id}/knowledge/search` | Search PULSE's knowledge |
| `GET` | `/api/pulse/{id}/eod-summary` | End-of-day status report |

Full interactive API docs available at `http://localhost:8888/api/docs` when the server is running.
