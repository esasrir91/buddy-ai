# Use Cases

End-to-end patterns built from verified Buddy AI APIs. Each combines a few core
pieces — model, tools, knowledge, memory, or a team — into something useful.

## Research assistant

An agent that searches the web, runs calculations, and writes up findings.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.tools.tavily import TavilyTools
from buddy.tools.python import PythonTools

assistant = Agent(
    name="research_assistant",
    model=OpenAIChat(id="gpt-4o"),
    tools=[TavilyTools(), PythonTools()],
    instructions=[
        "Search the web for current, credible sources.",
        "Verify any numbers by running Python.",
        "Summarize findings with a short bulleted list and cite sources.",
    ],
    show_tool_calls=True,
    markdown=True,
)

assistant.print_response("Summarize the state of solar panel efficiency in 2026.")
```

!!! note "Keys"
    Needs `OPENAI_API_KEY` and `TAVILY_API_KEY` (`pip install tavily-python`).

## Customer-support bot with memory

A support agent that remembers each user across turns using persistent memory
and session storage.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.memory.v2.memory import Memory
from buddy.memory.v2.db.sqlite import SqliteMemoryDb
from buddy.storage.sqlite import SqliteStorage

support = Agent(
    name="support_bot",
    model=OpenAIChat(id="gpt-4o-mini"),
    memory=Memory(
        model=OpenAIChat(id="gpt-4o-mini"),
        db=SqliteMemoryDb(table_name="support_memories", db_file="tmp/support.db"),
    ),
    enable_user_memories=True,
    storage=SqliteStorage(table_name="support_sessions", db_file="tmp/support.db"),
    add_history_to_messages=True,
    num_history_runs=5,
    instructions=[
        "You are a friendly customer-support agent.",
        "Use what you remember about the user to personalize replies.",
        "If you cannot resolve an issue, summarize it for a human agent.",
    ],
    markdown=True,
)

support.print_response("Hi, my order #4471 hasn't arrived.", user_id="cust_88", session_id="ticket_4471")
support.print_response("Any update on that?", user_id="cust_88", session_id="ticket_4471")
```

**Why it works:** `Memory` + `enable_user_memories` captures durable facts about
the user; `storage` persists the session so a conversation can be resumed by its
`session_id`; `add_history_to_messages` keeps recent turns in context.

## Document Q&A over PDFs

Index a folder of PDFs and answer questions grounded in their content.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.knowledge.pdf import PDFKnowledgeBase
from buddy.vectordb.chroma import ChromaDb

knowledge = PDFKnowledgeBase(
    path="docs/policies/",  # a PDF file or a directory of PDFs
    vector_db=ChromaDb(collection="policies", persistent_client=True),
)
knowledge.load()  # run once; re-run with recreate=True to rebuild

qa = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    knowledge=knowledge,
    search_knowledge=True,
    instructions=["Answer only from the documents.", "Quote the relevant passage."],
    markdown=True,
)

qa.print_response("What is the refund policy for damaged items?")
```

!!! tip "Filtered retrieval"
    If you attached metadata to documents, restrict retrieval with
    `qa.run(question, knowledge_filters={"category": "returns"})`.

## Data analysis agent

An agent that writes and runs Python to analyze data and report results.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.tools.python import PythonTools
from buddy.tools.calculator import CalculatorTools

analyst = Agent(
    name="data_analyst",
    model=OpenAIChat(id="gpt-4o"),
    tools=[PythonTools(), CalculatorTools()],
    instructions=[
        "Write Python to load and analyze the data.",
        "Show the code and the computed result.",
        "Explain findings in plain language.",
    ],
    show_tool_calls=True,
    markdown=True,
)

analyst.print_response(
    "Given monthly revenue [120, 135, 150, 128, 162], compute the mean, "
    "the month-over-month growth, and the overall trend."
)
```

**What to expect:** the agent emits Python via `PythonTools`, runs it, and
returns the numeric results alongside an explanation.

## Structured extraction pipeline

Combine tools with `response_model` to return validated, typed data.

```python
from pydantic import BaseModel
from buddy import Agent
from buddy.models.openai import OpenAIChat

class Contact(BaseModel):
    name: str
    email: str
    company: str | None = None

extractor = Agent(model=OpenAIChat(id="gpt-4o"), response_model=Contact)

result = extractor.run("Reach out to Dana Lee at dana@acme.io from Acme Corp.")
contact = result.content  # a validated Contact instance
print(contact.name, contact.email, contact.company)
```
