"""
Buddy AI Agent App
A simple conversational agent powered by Buddy AI.
"""
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    name="MyAgent",
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "You are a helpful, friendly AI assistant.",
        "Be concise and clear in your responses.",
    ],
    markdown=True,
)

if __name__ == "__main__":
    agent.print_response("Hello! What can you help me with?", stream=True)
