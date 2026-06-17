"""
Buddy AI Agent API
A FastAPI-based REST API for your Buddy AI agent.
"""
from fastapi import FastAPI
from pydantic import BaseModel

from buddy import Agent
from buddy.models.openai import OpenAIChat

app = FastAPI(title="Buddy Agent API", version="1.0.0")

agent = Agent(
    name="APIAgent",
    model=OpenAIChat(id="gpt-4o"),
    instructions=["You are a helpful AI assistant exposed via REST API."],
    markdown=False,
)


class ChatRequest(BaseModel):
    message: str
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    agent: str


@app.get("/")
async def health():
    return {"status": "ok", "agent": agent.name}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    response = agent.run(request.message)
    return ChatResponse(
        response=response.content if response else "",
        agent=agent.name,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
