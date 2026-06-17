# Agent App

A Buddy AI agent application template.

## Setup

1. Copy `workspace/example_secrets` to `workspace/secrets` and fill in your API keys.
2. Install dependencies: `pip install buddy-ai`
3. Run the app: `python app.py`

## Structure

```
agent-app/
├── app.py                        # Main agent entrypoint
├── workspace/
│   ├── settings.py               # Workspace configuration
│   └── secrets/                  # API keys (git-ignored)
│       └── .env
└── README.md
```

## Usage

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    name="MyAgent",
    model=OpenAIChat(id="gpt-4o"),
    instructions="You are a helpful assistant.",
)
agent.print_response("Hello!")
```
