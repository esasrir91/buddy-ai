# Quick Start Guide

Get up and running with Buddy AI in minutes! This guide will walk you through creating your first AI agent and demonstrate core features.

## Prerequisites

- Python 3.10 or higher
- OpenAI API key (or another supported provider)

## 1. Installation

```bash
pip install buddy-ai[all]
```

## 2. Environment Setup

Create a `.env` file in your project directory:

```env
OPENAI_API_KEY=your-openai-api-key-here
```

Or set the environment variable:

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

## 3. Your First Agent

Create a file called `my_first_agent.py`:

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

# Create a simple agent
agent = Agent(
    name="MyFirstAgent",
    model=OpenAIChat(),
    instructions="You are a helpful assistant that provides clear and concise answers."
)

# Have a conversation
response = agent.run("Hello! What can you help me with?")
print(response.content)

# Follow-up question (memory is preserved)
response = agent.run("Can you remember what I just asked you?")
print(response.content)
```

Run it:
```bash
python my_first_agent.py
```

## 4. Agent with Memory

Add persistent memory to your agent:

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.memory.agent import AgentMemory

# Agent with memory
agent = Agent(
    name="MemoryBot",
    model=OpenAIChat(),
    memory=AgentMemory(),  # Enable memory
    instructions="You are a helpful assistant. Remember information about users."
)

# First conversation
response = agent.run("Hi, my name is Alice and I'm a software engineer.")
print(response.content)

# Later conversation (agent remembers Alice)
response = agent.run("What do you know about me?")
print(response.content)
```

## 5. Agent with Tools

Add web search capability:

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.tools.web import DuckDuckGoSearch
from buddy.memory.agent import AgentMemory

# Agent with tools
agent = Agent(
    name="SearchBot",
    model=OpenAIChat(),
    memory=AgentMemory(),
    tools=[DuckDuckGoSearch()],  # Add web search tool
    instructions=\"\"\"You are a research assistant.
    Use web search when you need current information.
    Always provide sources for your information.\"\"\"
)

# Ask for current information
response = agent.run("What are the latest developments in AI this week?")
print(response.content)
```

## 6. Agent with Knowledge Base

Add document knowledge:

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.knowledge.agent import AgentKnowledge

# Create knowledge base
knowledge = AgentKnowledge()

# Add some documents (you can use URLs, files, or text)
knowledge.add_text(\"\"\"
Company Policy: Remote Work Guidelines
- Employees can work remotely up to 3 days per week
- Core hours are 9 AM - 3 PM in your local timezone
- All meetings should be hybrid-friendly
- Use company Slack for communication
\"\"\")

# Agent with knowledge
agent = Agent(
    name="PolicyBot",
    model=OpenAIChat(),
    knowledge=knowledge,
    instructions="You are a company policy assistant. Use the knowledge base to answer questions."
)

# Ask about company policies
response = agent.run("What is our remote work policy?")
print(response.content)
```

## 7. Multi-Agent Team

Create a team of specialized agents:

```python
from buddy import Agent, Team
from buddy.models.openai import OpenAIChat
from buddy.tools.web import DuckDuckGoSearch
from buddy.tools.calculator import Calculator

# Create specialized agents
researcher = Agent(
    name="Researcher",
    model=OpenAIChat(),
    tools=[DuckDuckGoSearch()],
    instructions="You are a research specialist. Find and analyze information."
)

analyst = Agent(
    name="Analyst",
    model=OpenAIChat(),
    tools=[Calculator()],
    instructions="You are a data analyst. Analyze numbers and provide insights."
)

writer = Agent(
    name="Writer",
    model=OpenAIChat(),
    instructions="You are a content writer. Create well-structured, engaging content."
)

# Create a team
team = Team(
    agents=[researcher, analyst, writer],
    orchestrator=OpenAIChat()
)

# Team collaboration
response = team.run(\"\"\"
Research the current state of electric vehicle adoption,
analyze the growth trends, and write a brief report.
\"\"\")

print(response.content)
```

## 8. Streaming Responses

Get real-time streaming responses:

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

agent = Agent(
    name="StreamingBot",
    model=OpenAIChat(),
    instructions="You are a storyteller. Create engaging narratives."
)

# Stream the response
print("Agent: ", end="", flush=True)
for chunk in agent.stream_run("Tell me a short story about a robot learning to paint"):
    print(chunk.content, end="", flush=True)
print()  # New line at the end
```

## 9. Custom Tools

Create your own tools:

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.tools import tool
import requests

@tool
def get_weather(city: str) -> str:
    \"\"\"Get current weather for a city.
    
    Args:
        city: Name of the city
    
    Returns:
        Weather information
    \"\"\"
    # Example using a weather API
    # In real usage, you'd use an actual weather service
    return f"The weather in {city} is sunny and 72°F"

@tool
def calculate_tip(bill_amount: float, tip_percentage: float = 15.0) -> str:
    \"\"\"Calculate tip amount.
    
    Args:
        bill_amount: Total bill amount
        tip_percentage: Tip percentage (default 15%)
    
    Returns:
        Tip calculation
    \"\"\"
    tip_amount = bill_amount * (tip_percentage / 100)
    total = bill_amount + tip_amount
    return f"Bill: ${bill_amount:.2f}, Tip ({tip_percentage}%): ${tip_amount:.2f}, Total: ${total:.2f}"

# Agent with custom tools
agent = Agent(
    name="HelperBot",
    model=OpenAIChat(),
    tools=[get_weather, calculate_tip],
    instructions="You are a helpful assistant with weather and calculation tools."
)

# Use custom tools
response = agent.run("What's the weather in New York?")
print(response.content)

response = agent.run("If my bill is $85.50, what's a 20% tip?")
print(response.content)
```

## 10. Deployment with FastAPI

Create a web API for your agent:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from buddy import Agent
from buddy.models.openai import OpenAIChat

# Create FastAPI app
app = FastAPI()

# Create agent
agent = Agent(
    name="APIBot",
    model=OpenAIChat(),
    instructions="You are an API assistant. Provide helpful responses."
)

# Request model
class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"

# Response model  
class ChatResponse(BaseModel):
    response: str
    agent_name: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    response = agent.run(request.message, user_id=request.user_id)
    return ChatResponse(
        response=response.content,
        agent_name=agent.name
    )

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Run the API:
```bash
python api_agent.py
```

Test it:
```bash
curl -X POST "http://localhost:8000/chat" \\
     -H "Content-Type: application/json" \\
     -d '{"message": "Hello, API!", "user_id": "user123"}'
```

## Next Steps

Now that you've got the basics down, explore these advanced features:

### 📚 Core Concepts
- [Agent Configuration](../agents/configuration.md) - Advanced agent setup
- [Memory System](../memory/overview.md) - Persistent memory and user data
- [Tools & Functions](../tools/overview.md) - Custom tool development

### 🚀 Advanced Features  
- [Multi-Agent Teams](../team/overview.md) - Collaborative AI systems
- [Workflows](../workflows/overview.md) - Process automation
- [Multi-Modal AI](../advanced/multimodal.md) - Images, audio, video

### 🛠️ Integration & Deployment
- [FastAPI Apps](../deployment/fastapi.md) - Web API development
- [Docker Deployment](../deployment/docker.md) - Containerization
- [CLI Tools](../cli/overview.md) - Command-line interface

### 📖 Examples & Use Cases
- [Basic Examples](../examples/basic.md) - More example implementations
- [Advanced Examples](../examples/advanced.md) - Complex use cases
- [Integration Examples](../examples/integrations.md) - Third-party integrations

## Common Patterns

### Configuration Pattern
```python
# config.py
import os
from buddy import Agent
from buddy.models.openai import OpenAIChat

def create_agent(name: str, instructions: str) -> Agent:
    return Agent(
        name=name,
        model=OpenAIChat(
            model=os.getenv("MODEL_NAME", "gpt-4"),
            temperature=float(os.getenv("TEMPERATURE", "0.7"))
        ),
        instructions=instructions
    )
```

### Error Handling Pattern
```python
from buddy.exceptions import ModelProviderError, MemoryError

def safe_agent_run(agent: Agent, message: str) -> str:
    try:
        response = agent.run(message)
        return response.content
    except ModelProviderError as e:
        return f"Model error: {e}"
    except MemoryError as e:
        return f"Memory error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"
```

### Monitoring Pattern
```python
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def monitored_agent_run(agent: Agent, message: str) -> str:
    logger.info(f"Agent {agent.name} received message: {message[:50]}...")
    
    response = agent.run(message)
    
    logger.info(f"Response generated. Tokens: {response.metrics.total_tokens}")
    
    return response.content
```

Ready to build amazing AI agents? Check out the detailed documentation for advanced features and best practices!