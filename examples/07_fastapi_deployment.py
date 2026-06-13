"""
07_fastapi_deployment.py — Deploy an agent as a FastAPI REST API

Run with:
    python examples/07_fastapi_deployment.py

Then call it:
    curl -X POST http://localhost:7777/runs \
      -H "Content-Type: application/json" \
      -d '{"message": "What is 2 + 2?"}'

Install:
    pip install buddy-ai

Set your API key:
    export OPENAI_API_KEY=sk-...
"""

from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.app.fastapi import FastAPIApp

agent = Agent(
    name="api_agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions="You are a helpful assistant.",
    markdown=True,
)

app = FastAPIApp(agents=[agent], port=7777)

if __name__ == "__main__":
    app.serve()
