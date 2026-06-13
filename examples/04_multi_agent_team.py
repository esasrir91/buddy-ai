"""
04_multi_agent_team.py — Two agents collaborating as a team

Demonstrates a Team where a coordinator delegates to specialist agents.

Install:
    pip install buddy-ai tavily-python

Set API keys:
    export OPENAI_API_KEY=sk-...
    export TAVILY_API_KEY=tvly-...
"""

from buddy import Agent, Team
from buddy.models.openai import OpenAIChat
from buddy.tools.tavily import TavilyTools

researcher = Agent(
    name="researcher",
    role="Find accurate and up-to-date information on any topic",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[TavilyTools()],
    show_tool_calls=True,
)

writer = Agent(
    name="writer",
    role="Write clear, engaging, well-structured content",
    model=OpenAIChat(id="gpt-4o"),
    instructions=["Always use markdown formatting.", "Include headers and bullet points."],
)

team = Team(
    name="content_team",
    agents=[researcher, writer],
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "First, have the researcher gather facts.",
        "Then, have the writer compose the final piece.",
    ],
    markdown=True,
)

if __name__ == "__main__":
    team.print_response(
        "Write a 300-word article about recent advances in quantum computing."
    )
