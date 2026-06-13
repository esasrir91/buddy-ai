"""
03_agent_with_memory.py — Persistent agent that remembers across sessions

Demonstrates session memory: the agent recalls what was said earlier.

Install:
    pip install buddy-ai

Set your API key:
    export OPENAI_API_KEY=sk-...
"""

from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.memory.v2.memory import Memory
from buddy.storage.sqlite import SqliteStorage

agent = Agent(
    name="memory_agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    memory=Memory(
        db=SqliteStorage(table_name="agent_sessions", db_file="tmp/memory.db"),
    ),
    enable_user_memories=True,
    instructions=[
        "You are a personal assistant with memory.",
        "Reference past conversations when relevant.",
    ],
    markdown=True,
)

if __name__ == "__main__":
    user_id = "alice"

    # Turn 1
    agent.print_response(
        "My name is Alice and I love hiking.",
        user_id=user_id,
        session_id="session_001",
    )

    # Turn 2 — agent should remember Alice's name and interests
    agent.print_response(
        "What do you know about me?",
        user_id=user_id,
        session_id="session_001",
    )
