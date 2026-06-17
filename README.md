<div align="center">

# 🤖 Buddy AI

**A model-agnostic Python framework for building production-grade AI agents**

[![PyPI version](https://badge.fury.io/py/buddy-ai.svg)](https://pypi.org/project/buddy-ai/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/esasrir91/buddy-ai.svg)](https://github.com/esasrir91/buddy-ai/stargazers)

**[Documentation](https://esasrir91.github.io/buddy-ai/) · [GitHub](https://github.com/esasrir91/buddy-ai) · [CHANGELOG](https://github.com/esasrir91/buddy-ai/blob/main/CHANGELOG.md) · [Examples](https://github.com/esasrir91/buddy-ai/tree/main/examples)**

</div>

---

## What is Buddy AI?

Buddy AI is a comprehensive Python framework for creating, deploying, and managing intelligent AI agents. It provides a unified interface across 25+ LLM providers, a powerful memory system, extensible tools, RAG-based knowledge management, multi-agent teams, and workflows — all production-ready out of the box.

**New in v2.2.0 → [Competency Engine](#whats-new-in-v220)** — a balance-aware competency score that routes tasks to the most competent member and prioritizes what to train next.

**v2.1.0 → [PULSE](#-pulse--virtual-employees-era)** — give your AI an employee identity, teach it through interactive knowledge transfer, have it attend meetings, manage tasks, and more.

---

## Installation

```bash
# Core install
pip install buddy-ai

# With all optional dependencies (recommended)
pip install buddy-ai[all]

# Specific providers
pip install buddy-ai[openai]
pip install buddy-ai[anthropic]
pip install buddy-ai[google]
pip install buddy-ai[groq]

# Ecosystem integrations
pip install buddy-ai[langchain]   # use Buddy models/agents/tools in LangChain
pip install buddy-ai[langgraph]   # run Buddy agents as LangGraph nodes
```

---

## Quick Start

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    name="Assistant",
    model=OpenAIChat(),
    instructions="You are a helpful assistant."
)

response = agent.run("What can you do?")
print(response.content)
```

---

## ✨ PULSE — Virtual Employee's ERA

> **The flagship feature of v2.1.0**

PULSE turns a Buddy AI agent into a fully-functional **virtual human team member** — complete with a professional identity, the ability to learn from documents and live human sessions (KT), attend meetings, manage tasks, and communicate across channels.

### Launch the PULSE web UI

```bash
pip install buddy-ai[all]

# Set your LLM key
export OPENAI_API_KEY=sk-...

# Start the dashboard (or configure the key inside the UI)
buddy pulse start
# Open http://localhost:8888
```

### Or use PULSE in Python

```python
from buddy.pulse import PulseEmployee
from buddy.pulse.identity import EmployeeProfile
from buddy.models.openai import OpenAIChat

# Create the employee
priya = PulseEmployee(
    employee_profile=EmployeeProfile(
        full_name="Priya Sharma",
        role="Senior Backend Engineer",
        department="Engineering",
        skills=["Python", "FastAPI", "PostgreSQL"],
        timezone="Asia/Kolkata",
    ),
    model=OpenAIChat(id="gpt-4o"),
)

# Introduce herself
print(priya.introduce_yourself())

# Learn from a document
summary = priya.take_kt(
    source="architecture.md",
    session_name="Payments Architecture",
    knowledge_giver="Arjun Nair",
)
print(f"Confidence: {summary.confidence_score:.0%}")
print(f"Mental model: {summary.mental_model}")

# Start a live interactive KT session
session = priya.start_live_kt(
    session_name="Auth Service Deep Dive",
    knowledge_giver="Rahul",
)

# Human explains, Priya asks targeted questions
turn = session.human_explains("Our auth uses JWT with RS256...")
print(turn.pulse_message)  # Priya's response + questions
print(turn.questions)      # Clarifying questions

# Attend a meeting and extract actions
notes = priya.attend_meeting(
    transcript="Alice: Let's ship the new API by Friday...",
    title="Sprint Planning",
)
for action in notes.action_items:
    print(f"[{action.priority}] {action.description} → {action.owner}")

# Receive and track a task
task = priya.receive_task(
    title="Refactor payment retry logic",
    description="Reduce retry latency by 40%",
    priority="high",
    deadline="2026-06-20",
)
print(priya.report_status(task.task_id).message)
```

### PULSE Web UI — 9 pages

| Page | What it does |
|------|-------------|
| **Onboarding Wizard** | 4-step setup: identity → company/role → skills → launch |
| **Dashboard** | KT stats, active tasks, knowledge domains |
| **KT Center** | Launch live (chat) or async (document/URL) KT sessions |
| **Live KT Session** | 3-panel view: dialogue + real-time Confidence Meter + Mental Model |
| **Meeting Room** | Paste transcript → extract decisions + action items instantly |
| **Task Board** | Kanban board with move buttons and status updates |
| **Chat** | WebSocket streaming chat directly with your PULSE employee |
| **Knowledge Explorer** | Search across everything PULSE has learned |
| **Settings** | Configure AI model, API keys, and employee profile |

### Desktop app (Windows & Mac)

Run PULSE as a native desktop app with system tray support — the autonomous worker keeps running when you close the window.

```bash
pip install buddy-ai[all]
cd pulse-ui && npm install && npm run build
cd ../pulse-desktop && npm install && npm start
```

Build installers: `npm run build:win` or `npm run build:mac`. See [pulse-desktop/README.md](pulse-desktop/README.md).

---

## Core Features

### 🤖 Agent System

```python
from buddy import Agent
from buddy.models.anthropic import Claude
from buddy.tools.tavily import TavilyTools
from buddy.memory.agent import AgentMemory

agent = Agent(
    name="ResearchBot",
    model=Claude(id="claude-opus-4-5"),
    tools=[TavilyTools()],
    memory=AgentMemory(),
    instructions="You are a research assistant.",
    markdown=True,
)

response = agent.run("Latest developments in quantum computing?")
```

### 🧠 25+ Model Providers

```python
from buddy.models.openai import OpenAIChat
from buddy.models.anthropic import Claude
from buddy.models.google import Gemini
from buddy.models.groq import Groq
from buddy.models.ollama import Ollama

# Local model via Ollama
agent = Agent(model=Ollama(id="llama3.2"))

# Switch models at runtime
agent.model = Claude(id="claude-sonnet-4-5")
```

### 🛠️ Tools

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.tools import tool
from buddy.tools.python import PythonTools
from buddy.tools.file import FileTools

# Built-in toolkits
agent = Agent(model=OpenAIChat(), tools=[PythonTools(), FileTools()])

# Custom tool with the @tool decorator
@tool
def get_stock_price(ticker: str) -> str:
    """Get real-time stock price for a ticker symbol."""
    return fetch_price(ticker)

# Plain functions work too — just pass them in `tools=[...]`
agent = Agent(model=OpenAIChat(), tools=[get_stock_price])
```

### 🧠 Memory & Knowledge (RAG)

```python
from buddy.knowledge.pdf import PDFKnowledgeBase
from buddy.vectordb.chroma import ChromaDb

knowledge = PDFKnowledgeBase(
    path="company_handbook.pdf",
    vector_db=ChromaDb(collection="handbook"),
)

agent = Agent(
    model=OpenAIChat(),
    knowledge=knowledge,
    search_knowledge=True,
)
```

### 👥 Multi-Agent Teams

```python
from buddy import Agent, Team

researcher = Agent(name="Researcher", role="Research the topic")
writer = Agent(name="Writer", role="Write a clear summary")
reviewer = Agent(name="Reviewer", role="Review and improve")

team = Team(
    members=[researcher, writer, reviewer],
    mode="coordinate",  # "route" | "coordinate" | "collaborate"
    instructions="Produce a polished research report.",
)

response = team.run("Write a report on renewable energy trends.")
```

### ⚙️ Workflows

```python
from buddy.workflow.workflow import Workflow

class ResearchWorkflow(Workflow):
    def run(self, topic: str):
        research = self.researcher.run(f"Research: {topic}")
        draft = self.writer.run(f"Write based on: {research.content}")
        return self.reviewer.run(f"Review: {draft.content}")
```

---

## CLI

```bash
# Initialize Buddy configuration
buddy init

# PULSE virtual employee
buddy pulse start             # Launch web UI (http://localhost:8888)
buddy pulse create            # Interactive employee setup
buddy pulse kt --source doc.pdf --name "KT Session" --giver Alice
buddy pulse status            # Module health check

# Training
buddy train /data --name my-model

# Desktop app (Windows & Mac)
cd pulse-desktop && npm install && npm start
```

---

## Deployment

```python
# FastAPI
from buddy.app.fastapi import FastAPIApp

app = FastAPIApp(agents=[agent])
app.serve(app="my_module:app", host="0.0.0.0", port=7777)
```

```dockerfile
# Docker
FROM python:3.12-slim
RUN pip install buddy-ai[all]
COPY . /app
WORKDIR /app
CMD ["buddy", "pulse", "start", "--host", "0.0.0.0"]
```

---

## What's New in v2.2.0

- **Competency Engine** — a balance-aware competency score (`buddy.eval.competency`) for agents and teams, decomposing competency into *vertical* (per-domain depth), *crosswise* (dependency-weighted cross-domain interaction), and *deficit* (gap to mastery) components.
- **Autonomous learning loop** — `AutonomousCompetencyLoop` reads live signals, scores competency, and automatically enqueues training jobs for the weakest, highest-leverage gaps.
- **Runtime competency routing** — `buddy.eval.competency_runtime` infers a task's domain, routes it to the most competent member, adapts the execution policy/model tier, and feeds the outcome back into a live tracker.
- **LangChain & LangGraph integrations** — `buddy.integrations` adds dependency-light adapters: use any Buddy model as a LangChain `BaseChatModel` (`BuddyChatModel`), expose Buddy agents as LangChain tools (`BuddyAgentTool`), convert tools/messages both ways, drop Buddy agents into a LangGraph `StateGraph` (`BuddyNode`, `build_sequential_graph`), and route between members with the Competency Engine (`make_competency_edge`).
- **Docs & examples** — see [Competency Engine](https://esasrir91.github.io/buddy-ai/advanced/competency/), [Integrations](https://esasrir91.github.io/buddy-ai/integrations/overview/), `examples/12_competency_engine.py`, and `examples/13_langchain_langgraph.py`.

[Full CHANGELOG →](https://github.com/esasrir91/buddy-ai/blob/main/CHANGELOG.md)

---

## What's New in v2.1.0

- **PULSE** — Virtual Employee's ERA: identity, interactive KT, meetings, tasks, comms, feedback, onboarding
- **PULSE Web UI** — Full React 18 + TypeScript dashboard with 9 pages
- **Live KT** — Real-time dialogue with Confidence Meter and Mental Model panel
- **LLM Settings UI** — Configure provider, model, and API key directly in the browser
- **36 unit tests** — Full test coverage for all PULSE modules
- **Bug fix** — `ProfessionalMemory` composition refactor

[Full CHANGELOG →](https://github.com/esasrir91/buddy-ai/blob/main/CHANGELOG.md)

---

## Optional Dependencies

| Extra | Installs |
|-------|---------|
| `buddy-ai[openai]` | OpenAI SDK |
| `buddy-ai[anthropic]` | Anthropic SDK |
| `buddy-ai[google]` | Google Generative AI SDK |
| `buddy-ai[groq]` | Groq SDK |
| `buddy-ai[aws]` | boto3 (AWS Bedrock) |
| `buddy-ai[training]` | PyTorch, Transformers, PEFT |
| `buddy-ai[multimodal]` | Pillow, OpenCV, librosa |
| `buddy-ai[tools]` | Playwright, Selenium, Slack SDK |
| `buddy-ai[all]` | Everything above |

---

## Links

- **Documentation**: [esasrir91.github.io/buddy-ai](https://esasrir91.github.io/buddy-ai/)
- **GitHub**: [github.com/esasrir91/buddy-ai](https://github.com/esasrir91/buddy-ai)
- **PyPI**: [pypi.org/project/buddy-ai](https://pypi.org/project/buddy-ai/)
- **Issues**: [github.com/esasrir91/buddy-ai/issues](https://github.com/esasrir91/buddy-ai/issues)
- **Discussions**: [github.com/esasrir91/buddy-ai/discussions](https://github.com/esasrir91/buddy-ai/discussions)

---

## License

MIT License — see [LICENSE](https://github.com/esasrir91/buddy-ai/blob/main/LICENSE)

---

<div align="center">
Built with ❤️ by <a href="https://github.com/esasrir91">Sriram Sangeeth Mantha</a>
</div>
