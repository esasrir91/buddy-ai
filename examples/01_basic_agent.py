"""
01_basic_agent.py — Hello World with buddy-ai

The simplest possible agent: give it a model and run a prompt.

Install:
    pip install buddy-ai

Set your API key:
    export OPENAI_API_KEY=sk-...
"""

from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    name="assistant",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions="You are a helpful assistant. Be concise.",
    markdown=True,
)

if __name__ == "__main__":
    agent.print_response("What is the capital of France?")
