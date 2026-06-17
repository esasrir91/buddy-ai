# Agent API

A Buddy AI agent REST API template using FastAPI.

## Setup

1. Copy `workspace/example_secrets` to `workspace/secrets` and fill in your API keys.
2. Install dependencies: `pip install buddy-ai fastapi uvicorn`
3. Start the API: `uvicorn api:app --reload`

## Endpoints

- `GET /` — Health check
- `POST /chat` — Send a message to the agent
- `GET /docs` — Interactive API docs (Swagger UI)

## Structure

```
agent-api/
├── api.py                        # FastAPI application
├── workspace/
│   ├── settings.py               # Workspace configuration
│   └── secrets/                  # API keys (git-ignored)
│       └── .env
└── README.md
```
