# LangChain Integration

`buddy.integrations.langchain` bridges Buddy and the LangChain ecosystem in both
directions.

```bash
pip install "buddy-ai[langchain]"
```

```python
from buddy.integrations.langchain import (
    BuddyChatModel,
    BuddyAgentTool,
    to_langchain_tool,
    from_langchain_tool,
    to_buddy_messages,
    from_buddy_message,
)
```

## Buddy model → LangChain chat model

`BuddyChatModel` wraps any `buddy.models` model as a LangChain `BaseChatModel`.
This means Buddy's unified provider layer (OpenAI, Anthropic, Google, Cohere,
AWS, Azure, Ollama, Groq, …) can drive LangChain chains, agents, and LangGraph
nodes — one model object, every provider.

```python
from buddy.models.openai import OpenAIChat
from buddy.integrations.langchain import BuddyChatModel

llm = BuddyChatModel(buddy_model=OpenAIChat(id="gpt-4o-mini"))

# Standard LangChain Runnable interface
print(llm.invoke("Say hello in French.").content)

# Works in LCEL chains
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([("human", "Translate to {lang}: {text}")])
chain = prompt | llm
print(chain.invoke({"lang": "German", "text": "good morning"}).content)
```

Both sync (`invoke`) and async (`ainvoke`) are supported; `_agenerate` calls the
Buddy model's `aresponse`.

!!! info "How it works"
    `BuddyChatModel` is a lightweight proxy until first construction, so importing
    the module never requires LangChain. On first use it builds a real
    `BaseChatModel` subclass against your installed `langchain-core`, converts
    LangChain messages to Buddy `Message` objects, calls `model.response(...)`,
    and returns a `ChatResult`.

## Buddy agent → LangChain tool

`BuddyAgentTool` exposes a full Buddy `Agent` or `Team` — with its own model,
tools, memory, and knowledge — as a single LangChain tool that other LangChain
agents can call.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.integrations.langchain import BuddyAgentTool

researcher = Agent(name="researcher", model=OpenAIChat(id="gpt-4o-mini"))

research_tool = BuddyAgentTool(
    researcher,
    name="research",
    description="Research a topic and return concise findings.",
).as_tool()

# `research_tool` is a langchain_core StructuredTool (sync + async).
```

## Tool conversion (both directions)

### Buddy → LangChain

```python
from buddy.tools import tool
from buddy.integrations.langchain import to_langchain_tool

@tool
def word_count(text: str) -> int:
    """Count the number of words in a piece of text."""
    return len(text.split())

lc_tool = to_langchain_tool(word_count)   # a StructuredTool
lc_tool.invoke({"text": "one two three"})  # -> 3
```

`to_langchain_tool` accepts a Buddy `Function` (from `@tool`) or any plain
callable; callables are wrapped via `Function.from_callable`.

### LangChain → Buddy

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.integrations.langchain import from_langchain_tool

buddy_fn = from_langchain_tool(lc_tool)   # a buddy Function

agent = Agent(model=OpenAIChat(id="gpt-4o-mini"), tools=[buddy_fn])
```

The converter extracts the tool's argument schema (pydantic v1 or v2
`args_schema`) into Buddy's JSON-schema parameter format, and delegates execution
to the LangChain tool's `run` method.

## Message conversion

```python
from langchain_core.messages import HumanMessage, SystemMessage
from buddy.integrations.langchain import to_buddy_messages, from_buddy_message
from buddy.models.message import Message

buddy_msgs = to_buddy_messages([SystemMessage(content="..."), HumanMessage(content="hi")])
lc_msg = from_buddy_message(Message(role="assistant", content="hello"))
```

Role mapping: `human↔user`, `ai↔assistant`, `system↔system`, `tool↔tool`
(preserving `tool_call_id`).

## API summary

| Symbol | Type | Description |
|--------|------|-------------|
| `BuddyChatModel(buddy_model=...)` | factory | LangChain `BaseChatModel` backed by a Buddy model |
| `BuddyAgentTool(agent, name=, description=).as_tool()` | class | Buddy agent/team as a LangChain tool |
| `to_langchain_tool(fn)` | function | Buddy `Function`/callable → LangChain `StructuredTool` |
| `from_langchain_tool(tool)` | function | LangChain `BaseTool` → Buddy `Function` |
| `to_buddy_messages(messages)` | function | LangChain messages → Buddy `Message` list |
| `from_buddy_message(message)` | function | Buddy `Message` → LangChain message |
