"""
02_agent_with_tools.py — Agent that can search the web and run Python code

Demonstrates attaching built-in tools to an agent.

Install:
    pip install buddy-ai tavily-python

Set API keys:
    export OPENAI_API_KEY=sk-...
    export TAVILY_API_KEY=tvly-...
"""

from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.tools.tavily import TavilyTools
from buddy.tools.python import PythonTools

agent = Agent(
    name="research_agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[TavilyTools(), PythonTools()],
    instructions=[
        "You are a research assistant.",
        "Use web search for current information.",
        "Run Python code to verify calculations.",
    ],
    show_tool_calls=True,
    markdown=True,
)

if __name__ == "__main__":
    agent.print_response(
        "What is the current price of Bitcoin? "
        "Then calculate how many BTC I could buy with $10,000."
    )
