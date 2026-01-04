# Agent Class Reference

The `Agent` class is the core component of Buddy AI, representing an intelligent AI entity with advanced capabilities including memory, tools, knowledge, personality, and evolution mechanisms.

## 📋 Class Overview

```python
class Agent:
    \"\"\"
    An intelligent AI agent with comprehensive capabilities.
    
    Supports multiple LLM providers, persistent memory, tool usage,
    knowledge integration, personality modeling, and evolutionary learning.
    \"\"\"
```

## 🏗️ Constructor

```python
Agent(
    # Core Configuration
    model: Model,
    name: str = None,
    agent_id: str = None,
    description: str = None,
    instructions: Union[str, List[str], Callable] = None,
    
    # Behavioral Settings  
    goal: str = None,
    expected_output: str = None,
    additional_context: str = None,
    markdown: bool = False,
    introduction: str = None,
    
    # Memory System
    memory: AgentMemory = None,
    add_history_to_messages: bool = True,
    num_history_runs: int = None,
    enable_agentic_memory: bool = False,
    enable_user_memories: bool = False,
    enable_session_summaries: bool = False,
    cache_session: bool = False,
    
    # Tools and Knowledge
    tools: List[Union[Toolkit, Callable]] = None,
    show_tool_calls: bool = False,
    tool_call_limit: int = None,
    knowledge: AgentKnowledge = None,
    search_knowledge: bool = True,
    read_chat_history: bool = True,
    
    # Advanced Features
    reasoning: bool = False,
    planning: bool = False,
    personality: PersonalityProfile = None,
    evolution: bool = False,
    
    # Session Management
    user_id: str = None,
    session_id: str = None,
    
    # Debugging and Monitoring
    debug_mode: bool = False,
    monitoring: bool = False,
    
    # Output Formatting
    response_format: str = None,
    max_tokens: int = None,
    temperature: float = None
)
```

## 📊 Core Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | `Model` | The language model that powers the agent (OpenAI, Anthropic, etc.) |

### Identity and Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | `None` | Human-readable name for the agent |
| `agent_id` | `str` | Auto-generated | Unique identifier for the agent |
| `description` | `str` | `None` | Brief description of agent's purpose and capabilities |
| `introduction` | `str` | `None` | Message agent shows when first interacting with users |

### Instructions and Behavior

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `instructions` | `str \| List[str] \| Callable` | `None` | System prompts defining agent behavior |
| `goal` | `str` | `None` | Primary objective the agent should accomplish |
| `expected_output` | `str` | `None` | Description of desired response format |
| `additional_context` | `str` | `None` | Extra context to improve responses |
| `markdown` | `bool` | `False` | Whether to format responses in markdown |

### Memory Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `memory` | `AgentMemory` | `None` | Memory system for persistent conversation storage |
| `add_history_to_messages` | `bool` | `True` | Include conversation history in context |
| `num_history_runs` | `int` | `None` | Number of previous conversations to include |
| `enable_agentic_memory` | `bool` | `False` | Allow agent to manage its own memories |
| `enable_user_memories` | `bool` | `False` | Store user-specific information across sessions |
| `enable_session_summaries` | `bool` | `False` | Generate automatic session summaries |
| `cache_session` | `bool` | `False` | Cache session data in memory for faster access |

### Tools and Knowledge

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tools` | `List[Toolkit \| Callable]` | `None` | Functions and tools the agent can use |
| `show_tool_calls` | `bool` | `False` | Display tool execution in responses |
| `tool_call_limit` | `int` | `None` | Maximum tool calls per interaction |
| `knowledge` | `AgentKnowledge` | `None` | Knowledge base for RAG capabilities |
| `search_knowledge` | `bool` | `True` | Enable knowledge base search |
| `read_chat_history` | `bool` | `True` | Allow reading conversation history |

### Advanced Features

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `reasoning` | `bool` | `False` | Enable advanced reasoning capabilities |
| `planning` | `bool` | `False` | Enable task planning and decomposition |
| `personality` | `PersonalityProfile` | `None` | Personality traits and communication style |
| `evolution` | `bool` | `False` | Enable self-improvement mechanisms |

## 🚀 Core Methods

### Interaction Methods

#### `run(message, **kwargs) -> RunResponse`
Execute a single interaction with the agent.

```python
response = agent.run(
    message="What's the weather like today?",
    user_id="user123",
    session_id="session456",
    stream=False,
    include_metadata=True
)

print(response.content)
print(response.metrics.total_tokens)
print(response.tool_calls)
```

**Parameters:**
- `message` (str): User input message
- `user_id` (str): User identifier for memory and personalization
- `session_id` (str): Session identifier for conversation grouping
- `stream` (bool): Whether to stream the response
- `include_metadata` (bool): Include execution metrics

**Returns:** `RunResponse` object with content, metrics, and metadata

#### `async_run(message, **kwargs) -> RunResponse`
Asynchronous version of run method.

```python
import asyncio

async def chat_with_agent():
    response = await agent.async_run("Hello, agent!")
    return response.content

result = asyncio.run(chat_with_agent())
```

#### `stream_run(message, **kwargs) -> Iterator[RunResponse]`
Stream responses in real-time chunks.

```python
print("Agent: ", end="", flush=True)
for chunk in agent.stream_run("Tell me a story"):
    print(chunk.content, end="", flush=True)
print()  # New line when done
```

#### `async_stream_run(message, **kwargs) -> AsyncIterator[RunResponse]`
Asynchronous streaming responses.

```python
async def stream_chat():
    async for chunk in agent.async_stream_run("Explain quantum physics"):
        print(chunk.content, end="", flush=True)
```

### Memory Management

#### `get_memories(user_id=None, limit=None, memory_type=None) -> List[Memory]`
Retrieve stored memories for analysis.

```python
# Get all memories for a user
memories = agent.get_memories(user_id="user123", limit=50)

# Get specific type of memories
preferences = agent.get_memories(
    user_id="user123",
    memory_type="user_preference"
)

for memory in memories:
    print(f"{memory.timestamp}: {memory.content}")
```

#### `add_memory(content, user_id=None, memory_type="fact") -> str`
Manually add memories to the agent's knowledge.

```python
# Add user preference
memory_id = agent.add_memory(
    content="User prefers detailed technical explanations",
    user_id="user123",
    memory_type="user_preference"
)

# Add factual information
agent.add_memory(
    content="The company's fiscal year ends in March",
    memory_type="company_fact"
)
```

#### `update_memory(memory_id, new_content) -> bool`
Modify existing memories.

```python
success = agent.update_memory(
    memory_id="mem_123",
    new_content="Updated information about the user"
)
```

#### `delete_memory(memory_id) -> bool`
Remove specific memories.

```python
agent.delete_memory("mem_456")
```

#### `clear_memory(user_id=None, memory_type=None) -> int`
Clear memories with optional filtering.

```python
# Clear all memories for a user
deleted_count = agent.clear_memory(user_id="user123")

# Clear specific type of memories
deleted_count = agent.clear_memory(memory_type="temporary")

# Clear all memories
agent.clear_memory()
```

#### `get_session_summary(session_id) -> str`
Get AI-generated summary of a conversation session.

```python
summary = agent.get_session_summary("session456")
print(summary)
```

### Tool Management

#### `add_tool(tool) -> None`
Add tools to the agent at runtime.

```python
from buddy.tools.calculator import Calculator
from buddy.tools.web import WebSearch

# Add single tool
agent.add_tool(Calculator())

# Add multiple tools
agent.add_tools([WebSearch(), Calculator()])
```

#### `remove_tool(tool_name) -> bool`
Remove tools from the agent.

```python
success = agent.remove_tool("calculator")
```

#### `list_tools() -> List[dict]`
Get information about available tools.

```python
tools = agent.list_tools()
for tool in tools:
    print(f"Name: {tool['name']}")
    print(f"Description: {tool['description']}")
    print(f"Parameters: {tool['parameters']}")
```

#### `get_tool(tool_name) -> Toolkit`
Get specific tool instance.

```python
calculator = agent.get_tool("calculator")
result = calculator.calculate("2 + 2")
```

### Knowledge Management

#### `add_knowledge(source, **kwargs) -> str`
Add various knowledge sources to the agent.

```python
# Add text knowledge
knowledge_id = agent.add_knowledge(
    "The company was founded in 2020 and specializes in AI solutions.",
    source_type="text",
    tags=["company_info"]
)

# Add PDF document
agent.add_knowledge(
    "path/to/manual.pdf",
    source_type="pdf",
    tags=["documentation", "manual"]
)

# Add website
agent.add_knowledge(
    "https://company.com/policies",
    source_type="url",
    tags=["policies"]
)
```

#### `search_knowledge(query, limit=5, filters=None) -> List[dict]`
Search the agent's knowledge base.

```python
results = agent.search_knowledge(
    query="company policies on remote work",
    limit=3,
    filters={"tags": ["policies", "hr"]}
)

for result in results:
    print(f"Score: {result['score']:.2f}")
    print(f"Source: {result['source']}")
    print(f"Content: {result['content'][:200]}...")
```

#### `update_knowledge(knowledge_id, new_content) -> bool`
Update existing knowledge entries.

```python
success = agent.update_knowledge(
    knowledge_id="kb_123",
    new_content="Updated company information..."
)
```

#### `remove_knowledge(knowledge_id) -> bool`
Remove knowledge entries.

```python
agent.remove_knowledge("kb_456")
```

### Configuration Management

#### `update_instructions(new_instructions) -> None`
Modify agent instructions at runtime.

```python
agent.update_instructions([
    "You are a helpful customer service agent.",
    "Always be polite and professional.",
    "Escalate complex issues to human agents."
])
```

#### `set_personality(personality_profile) -> None`
Set or update agent personality.

```python
from buddy.agent.personality import PersonalityProfile

personality = PersonalityProfile(
    traits={
        "extraversion": 0.7,
        "agreeableness": 0.8,
        "conscientiousness": 0.9
    },
    communication_style="professional",
    humor_level=0.3
)

agent.set_personality(personality)
```

#### `enable_feature(feature_name) -> None`
Enable advanced features at runtime.

```python
# Enable reasoning
agent.enable_feature("reasoning")

# Enable planning
agent.enable_feature("planning")

# Enable evolution
agent.enable_feature("evolution")
```

## 📊 Response Objects

### RunResponse
The main response object returned by agent interactions.

```python
class RunResponse:
    content: str              # Agent's response text
    metrics: ResponseMetrics  # Token usage, timing, costs
    tool_calls: List[dict]    # Tools used during response
    knowledge_used: List[dict] # Knowledge sources referenced
    reasoning_steps: List[str] # Reasoning process (if enabled)
    confidence_score: float   # Response confidence (0-1)
    sources: List[str]        # Information sources
    session_id: str           # Session identifier
    run_id: str              # Unique run identifier
    model_used: str          # Model that generated response
    tokens_used: int         # Total tokens consumed
    response_time: float     # Generation time in seconds
```

### ResponseMetrics
Detailed metrics about the agent's performance.

```python
class ResponseMetrics:
    total_tokens: int        # Input + output tokens
    input_tokens: int        # Tokens in prompt
    output_tokens: int       # Tokens in response
    cost: float             # Estimated cost in USD
    response_time: float    # Time to generate response
    tool_execution_time: float # Time spent executing tools
    knowledge_search_time: float # Time spent searching knowledge
    model_calls: int        # Number of model API calls
    cache_hits: int         # Number of cache hits
    cache_misses: int       # Number of cache misses
```

## 🔧 Advanced Configuration

### Custom Model Configuration
```python
from buddy.models.openai import OpenAIChat

# Detailed model configuration
model = OpenAIChat(
    model="gpt-4-turbo-preview",
    temperature=0.7,
    max_tokens=4000,
    top_p=0.9,
    frequency_penalty=0.1,
    presence_penalty=0.1,
    stop_sequences=["\\n\\n", "END"],
    seed=42,
    timeout=30,
    max_retries=3
)

agent = Agent(model=model)
```

### Advanced Memory Configuration
```python
from buddy.memory.agent import AgentMemory
from buddy.storage.postgres import PostgreSQLStorage

# Custom memory with external storage
memory = AgentMemory(
    storage=PostgreSQLStorage("postgresql://..."),
    max_memories=10000,
    memory_decay_rate=0.01,
    consolidation_threshold=0.8,
    enable_summarization=True,
    summary_frequency=10  # Summarize every 10 conversations
)

agent = Agent(model=model, memory=memory)
```

### Dynamic Instructions
```python
def get_dynamic_instructions():
    from datetime import datetime
    current_time = datetime.now()
    
    if current_time.hour < 12:
        greeting = "Good morning"
    elif current_time.hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
    
    return f\"\"\"{greeting}! You are a helpful assistant.
    Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
    Always be helpful, accurate, and up-to-date.\"\"\"

agent = Agent(
    model=model,
    instructions=get_dynamic_instructions
)
```

## 🚨 Error Handling

### Exception Types
```python
from buddy.exceptions import (
    AgentError,
    ModelProviderError,
    MemoryError,
    ToolExecutionError,
    KnowledgeError,
    ConfigurationError
)

try:
    response = agent.run("Hello!")
except ModelProviderError as e:
    print(f"Model error: {e}")
except MemoryError as e:
    print(f"Memory error: {e}")
except ToolExecutionError as e:
    print(f"Tool error: {e}")
except KnowledgeError as e:
    print(f"Knowledge error: {e}")
except AgentError as e:
    print(f"General agent error: {e}")
```

### Error Recovery
```python
def robust_agent_interaction(agent, message):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return agent.run(message)
        except ModelProviderError:
            if attempt < max_retries - 1:
                print(f"Retry attempt {attempt + 1}")
                continue
            else:
                return "I'm experiencing technical difficulties. Please try again later."
        except Exception as e:
            print(f"Unexpected error: {e}")
            return "An error occurred while processing your request."
```

## 📈 Performance Optimization

### Caching
```python
# Enable response caching
agent = Agent(
    model=model,
    cache_responses=True,
    cache_ttl=3600,  # 1 hour
    cache_size=1000
)
```

### Batch Processing
```python
# Process multiple messages efficiently
messages = ["Hello", "How are you?", "Goodbye"]

responses = agent.batch_run(
    messages=messages,
    batch_size=5,
    parallel=True
)
```

### Resource Management
```python
# Proper cleanup for long-running applications
try:
    # Agent interactions
    response = agent.run("Hello")
finally:
    # Cleanup resources
    agent.cleanup()
    # or use context manager
    with Agent(model=model) as agent:
        response = agent.run("Hello")
```

## 🎯 Best Practices

### Agent Design Principles
1. **Clear Purpose**: Define specific role and capabilities
2. **Appropriate Tools**: Only include necessary tools
3. **Memory Management**: Use appropriate memory settings
4. **Error Handling**: Implement robust error recovery
5. **Performance**: Monitor and optimize resource usage

### Configuration Guidelines
```python
# Good: Specific, focused agent
customer_service_agent = Agent(
    name="CustomerServiceBot",
    model=OpenAIChat(),
    instructions=[
        "You are a customer service representative.",
        "Be helpful, polite, and professional.",
        "Escalate complex issues to human agents.",
        "Always verify customer information before proceeding."
    ],
    tools=[EmailTools(), TicketingSystem()],
    memory=AgentMemory(),
    personality=PersonalityProfile(
        communication_style="professional",
        empathy_level=0.9
    )
)

# Avoid: Generic, unfocused agent
generic_agent = Agent(
    model=OpenAIChat(),
    instructions="Help with anything",
    tools=[All200Tools()],  # Too many tools
    # No memory or personality
)
```

## 📋 Complete Example

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.memory.agent import AgentMemory
from buddy.tools.web import WebSearch
from buddy.tools.calculator import Calculator
from buddy.knowledge.agent import AgentKnowledge
from buddy.agent.personality import PersonalityProfile

# Create comprehensive agent
agent = Agent(
    # Core configuration
    name="ResearchAssistant",
    model=OpenAIChat(model="gpt-4"),
    description="An AI research assistant with web access and calculation abilities",
    
    # Instructions
    instructions=[
        "You are a research assistant specializing in data analysis.",
        "Use web search for current information.",
        "Provide accurate calculations and cite sources.",
        "Always verify information from multiple sources."
    ],
    
    # Memory system
    memory=AgentMemory(),
    enable_user_memories=True,
    enable_session_summaries=True,
    
    # Tools
    tools=[WebSearch(), Calculator()],
    show_tool_calls=True,
    tool_call_limit=5,
    
    # Knowledge base
    knowledge=AgentKnowledge(),
    
    # Personality
    personality=PersonalityProfile(
        communication_style="academic",
        detail_level=0.8,
        confidence_threshold=0.7
    ),
    
    # Advanced features
    reasoning=True,
    planning=True,
    
    # Output formatting
    markdown=True,
    
    # Debugging
    debug_mode=False
)

# Use the agent
try:
    response = agent.run(
        "Research the latest developments in quantum computing and calculate "
        "the performance improvement over classical computers.",
        user_id="researcher_001"
    )
    
    print(f"Response: {response.content}")
    print(f"Tools used: {[call['tool'] for call in response.tool_calls]}")
    print(f"Confidence: {response.confidence_score}")
    print(f"Time taken: {response.response_time:.2f}s")
    print(f"Cost: ${response.metrics.cost:.4f}")
    
except Exception as e:
    print(f"Error: {e}")
    
finally:
    # Cleanup
    agent.cleanup()
```

This comprehensive Agent class provides the foundation for building sophisticated AI applications with advanced capabilities for memory, reasoning, tool usage, and knowledge management.