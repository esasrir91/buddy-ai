"""
09_streaming_agent.py — Stream tokens as they are generated

Demonstrates real-time streaming output, useful for chat UIs.

Install:
    pip install buddy-ai

Set your API key:
    export OPENAI_API_KEY=sk-...
"""

from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    name="streamer",
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions="Be detailed and verbose in your explanations.",
)

if __name__ == "__main__":
    print("Streaming response:\n")
    for chunk in agent.run_stream("Explain how neural networks learn, step by step."):
        print(chunk.content, end="", flush=True)
    print("\n\nStream complete.")
