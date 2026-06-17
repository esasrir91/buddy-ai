"""
Buddy AI Agent App
A simple conversational agent powered by Buddy AI.
"""
import os, sys
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pathlib import Path
from dotenv import load_dotenv

# Load API keys from workspace/secrets/.env
load_dotenv(Path(__file__).parent / "workspace" / "secrets" / ".env")

from buddy import Agent
from buddy.models.anthropic import Claude

agent = Agent(
    name="MyAgent",
    model=Claude(id="claude-sonnet-4-5"),
    instructions=[
        "You are a helpful, friendly AI assistant.",
        "Be concise and clear in your responses.",
    ],
    markdown=True,
)

if __name__ == "__main__":
    while True:
        message = input("You: ")
        if message.lower() in ("exit", "quit"):
            break
        agent.print_response(message, stream=True)
