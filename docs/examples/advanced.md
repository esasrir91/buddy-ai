# Advanced Examples

Patterns that combine multiple agents, retrieval, planning, and reasoning. All
snippets use verified APIs from the `buddy` package.

## Multi-agent team

A coordinator delegates to specialist agents. Members are passed via `members=`.

```python
from buddy import Agent, Team
from buddy.models.openai import OpenAIChat
from buddy.tools.tavily import TavilyTools

researcher = Agent(
    name="researcher",
    role="Find accurate, up-to-date information",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[TavilyTools()],
    show_tool_calls=True,
)

writer = Agent(
    name="writer",
    role="Write clear, well-structured content",
    model=OpenAIChat(id="gpt-4o"),
    instructions=["Use markdown.", "Include headers and bullet points."],
)

team = Team(
    name="content_team",
    members=[researcher, writer],
    mode="coordinate",
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "First, have the researcher gather facts.",
        "Then, have the writer compose the final piece.",
    ],
    markdown=True,
)

team.print_response("Write a 300-word article about recent advances in quantum computing.")
```

!!! warning "`members=`, not `agents=`"
    `Team` takes its participants through the required `members` parameter.

## RAG with a vector database

Index sources into a vector store, then let the agent search them.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.knowledge.url import UrlKnowledge
from buddy.vectordb.chroma import ChromaDb

knowledge = UrlKnowledge(
    urls=["https://example.com/handbook"],
    vector_db=ChromaDb(collection="handbook", persistent_client=True),
)
knowledge.load()  # read, chunk, embed, index

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    knowledge=knowledge,
    search_knowledge=True,
    instructions=["Search your knowledge base before answering.", "Cite sources."],
    markdown=True,
)

agent.print_response("What does the handbook say about onboarding?")
```

!!! note "Embeddings"
    `ChromaDb` uses `OpenAIEmbedder` by default, so an `OPENAI_API_KEY` is
    needed for indexing. Pass a different `embedder=` to use another provider.
    Buddy also ships an `irag` knowledge base (`buddy.knowledge.irag`) that uses
    spaCy + TF-IDF and needs no external vector DB.

## Planning agent

`PlanningAgent` decomposes a goal into an executable plan.

```python
from buddy.planning.planner import PlanningAgent, PlanStrategy

agent = PlanningAgent(
    name="planner",
    planning_strategy=PlanStrategy.HIERARCHICAL,
    plan_validation=True,
    adaptive_replanning=True,
    max_planning_depth=4,
)

plan = agent.create_execution_plan(
    goal="Research and summarize recent AI safety developments",
    context={"depth": "comprehensive"},
    constraints=["Stay within 500 words"],
    resources=["web_search", "document_reader"],
)

print(f"Goal: {plan.goal}")
for step in plan.steps:
    print(f"  [{step.step_type.value}] {step.name}: {step.description}")

validation = agent.validate_plan(plan)
print("Plan valid:", validation["valid"])
```

!!! note "Optional feature"
    Planning is an optional capability — check `check_feature("planning")` or
    `get_available_features()` at runtime.

## Reasoning

Enable step-by-step reasoning with `reasoning=True`. You can bound the number of
reasoning steps.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    reasoning=True,
    reasoning_min_steps=1,
    reasoning_max_steps=10,
    markdown=True,
)

response = agent.run("If a train travels 60 km in 45 minutes, what is its speed in km/h?")
print(response.content)
print(response.reasoning_content)  # the reasoning trace, when available
```

## Multi-model comparison

Run the same prompt across providers to compare latency and quality.

```python
import time
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.models.anthropic import Claude
from buddy.models.google import Gemini

PROMPT = "Explain the concept of entropy in 2 sentences."

models = [
    ("OpenAI", OpenAIChat(id="gpt-4o-mini")),
    ("Anthropic", Claude(id="claude-3-5-sonnet-20241022")),
    ("Google", Gemini(id="gemini-1.5-flash")),
]

for name, model in models:
    agent = Agent(name=name, model=model)
    start = time.perf_counter()
    response = agent.run(PROMPT)
    print(f"{name} ({time.perf_counter() - start:.2f}s): {response.content}")
```

!!! note "Provider extras and model ids"
    Each provider needs its extra (`pip install buddy-ai[anthropic]`,
    `[google]`, ...) and its own API key. The `id` strings above are
    illustrative — use whichever model ids your accounts have access to.
