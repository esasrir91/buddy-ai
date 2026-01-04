# Model Providers Overview

Buddy AI supports 25+ language model providers through a unified interface. This allows you to switch between providers seamlessly and take advantage of different models' strengths.

## Supported Providers

### Major Cloud Providers

| Provider | Models | Features |
|----------|--------|----------|
| **OpenAI** | GPT-4, GPT-4 Turbo, GPT-3.5 | Function calling, vision, embeddings |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 | Large context, advanced reasoning |
| **Google** | Gemini Pro, Gemini Ultra | Multi-modal, code generation |
| **AWS Bedrock** | Claude, Llama, Titan | Enterprise security, compliance |
| **Azure OpenAI** | GPT-4, GPT-3.5 | Enterprise integration |

### Open Source & Self-Hosted

| Provider | Models | Features |
|----------|--------|----------|
| **Ollama** | Llama, Mistral, CodeLlama | Local deployment, privacy |
| **Hugging Face** | Thousands of models | Open source, customizable |
| **vLLM** | Optimized inference | High performance, batching |
| **LM Studio** | Local models | Desktop deployment |

### Specialized Providers

| Provider | Specialty | Use Cases |
|----------|-----------|-----------|
| **Cohere** | Enterprise NLP | Classification, embeddings |
| **Fireworks** | Fast inference | Real-time applications |
| **Together AI** | Open source models | Cost-effective inference |
| **Groq** | Ultra-fast inference | Low-latency applications |

## Unified Interface

All providers use the same interface:

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.models.anthropic import AnthropicChat
from buddy.models.google import GoogleChat

# Same agent interface, different providers
openai_agent = Agent(model=OpenAIChat())
anthropic_agent = Agent(model=AnthropicChat())
google_agent = Agent(model=GoogleChat())

# Identical usage
response1 = openai_agent.run("Hello!")
response2 = anthropic_agent.run("Hello!")
response3 = google_agent.run("Hello!")
```

## Model Configuration

### Basic Configuration
```python
from buddy.models.openai import OpenAIChat

model = OpenAIChat(
    model="gpt-4",
    temperature=0.7,
    max_tokens=1000,
    top_p=1.0
)
```

### Advanced Configuration
```python
from buddy.models.openai import OpenAIChat

model = OpenAIChat(
    model="gpt-4",
    temperature=0.7,
    max_tokens=4000,
    top_p=0.9,
    frequency_penalty=0.1,
    presence_penalty=0.1,
    stop=["\\n\\n"],
    seed=42,
    timeout=30,
    max_retries=3,
    organization="org-xxx",
    base_url="https://custom-endpoint.com/v1"
)
```

## Model Selection Guide

### For Different Use Cases

**General Conversation**
- OpenAI GPT-4 Turbo
- Anthropic Claude 3.5 Sonnet
- Google Gemini Pro

**Code Generation**
- OpenAI GPT-4
- Google Gemini Pro
- Claude 3 Sonnet

**Large Context Tasks**
- Anthropic Claude 3 (200K tokens)
- Google Gemini Pro (128K tokens)
- OpenAI GPT-4 Turbo (128K tokens)

**Cost Optimization**
- OpenAI GPT-3.5 Turbo
- Together AI Llama models
- Ollama (self-hosted)

**Privacy & Compliance**
- Ollama (local deployment)
- AWS Bedrock
- Azure OpenAI

**Speed & Performance**
- Groq Llama
- Fireworks AI
- Together AI

## Model Switching

### Runtime Switching
```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.models.anthropic import AnthropicChat

agent = Agent(model=OpenAIChat())

# Switch model at runtime
agent.model = AnthropicChat()
response = agent.run("Hello with new model!")
```

### Fallback Models
```python
from buddy.models.openai import OpenAIChat
from buddy.models.anthropic import AnthropicChat

class FallbackModel:
    def __init__(self):\n        self.primary = OpenAIChat()
        self.fallback = AnthropicChat()
    
    def run(self, *args, **kwargs):
        try:
            return self.primary.run(*args, **kwargs)
        except Exception:
            return self.fallback.run(*args, **kwargs)

agent = Agent(model=FallbackModel())
```

## Performance Optimization

### Token Management
```python
# Efficient token usage
model = OpenAIChat(
    model="gpt-4",
    max_tokens=500,  # Limit output tokens
    temperature=0.3  # More deterministic = fewer retries
)
```

### Caching
```python
from buddy.models.openai import OpenAIChat

model = OpenAIChat(
    model="gpt-4",
    enable_caching=True,  # Enable response caching
    cache_ttl=3600       # Cache for 1 hour
)
```

### Batch Processing
```python
# Process multiple requests efficiently
messages = ["Hello", "Goodbye", "How are you?"]

responses = []
for message in messages:
    response = agent.run(message)
    responses.append(response)
```

## Model Comparison

### Feature Matrix

| Feature | OpenAI | Anthropic | Google | AWS | Azure |
|---------|--------|-----------|--------|-----|-------|
| Function Calling | ✅ | ✅ | ✅ | Varies | ✅ |
| Vision | ✅ | ✅ | ✅ | ✅ | ✅ |
| Code Generation | ✅ | ✅ | ✅ | ✅ | ✅ |
| Long Context | 128K | 200K | 128K | Varies | 128K |
| Streaming | ✅ | ✅ | ✅ | ✅ | ✅ |
| Enterprise | ✅ | ✅ | ✅ | ✅ | ✅ |

### Cost Comparison (Approximate)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| GPT-4 Turbo | $10 | $30 |
| Claude 3.5 Sonnet | $3 | $15 |
| Gemini Pro | $0.50 | $1.50 |
| GPT-3.5 Turbo | $0.50 | $1.50 |

*Prices are approximate and may change*

## Best Practices

### Model Selection
1. **Start with GPT-4 Turbo** for general use
2. **Use Claude 3** for large context tasks
3. **Try Gemini Pro** for code generation
4. **Consider cost** for high-volume applications
5. **Test multiple models** for your specific use case

### Error Handling
```python
from buddy.exceptions import ModelProviderError

try:
    response = agent.run("Hello!")
except ModelProviderError as e:
    print(f"Model error: {e}")
    # Switch to fallback model
    agent.model = fallback_model
    response = agent.run("Hello!")
```

### Monitoring
```python
# Track model usage
response = agent.run("Hello!")
print(f"Model: {response.model}")
print(f"Tokens used: {response.metrics.total_tokens}")
print(f"Cost: ${response.metrics.cost}")
```

## Provider-Specific Guides

- [OpenAI Configuration](openai.md)
- [Anthropic Configuration](anthropic.md)
- [Google AI Configuration](google.md)
- [AWS Bedrock Configuration](aws.md)
- [Azure OpenAI Configuration](azure.md)
- [Ollama Self-Hosting](ollama.md)
- [Custom Model Integration](custom.md)