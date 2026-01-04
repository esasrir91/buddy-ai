# Installation

## Requirements

- Python 3.10 or higher
- pip package manager

## Basic Installation

Install Buddy AI from PyPI:

```bash
pip install buddy-ai
```

## Installation with Provider Dependencies

### All Providers
Install with all supported model providers:
```bash
pip install buddy-ai[all]
```

### Specific Providers
Install only the providers you need:

```bash
# OpenAI only
pip install buddy-ai[openai]

# Anthropic only
pip install buddy-ai[anthropic]

# Google AI only
pip install buddy-ai[google]

# AWS Bedrock only
pip install buddy-ai[aws]

# Azure OpenAI only
pip install buddy-ai[azure]

# Multiple providers
pip install buddy-ai[openai,anthropic,google]
```

### Development Installation
For contributors and advanced users:

```bash
# Clone the repository
git clone https://github.com/esasrir91/buddy-ai.git
cd buddy-ai

# Install in development mode
pip install -e .[dev,all]
```

## Environment Setup

### API Keys
Set up your API keys as environment variables:

```bash
# OpenAI
export OPENAI_API_KEY="your-openai-key"

# Anthropic
export ANTHROPIC_API_KEY="your-anthropic-key"

# Google AI
export GOOGLE_API_KEY="your-google-key"

# Azure OpenAI
export AZURE_OPENAI_API_KEY="your-azure-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"

# AWS Bedrock
export AWS_ACCESS_KEY_ID="your-aws-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret"
export AWS_DEFAULT_REGION="us-east-1"

# Cohere
export COHERE_API_KEY="your-cohere-key"
```

### Configuration File
Create a `.env` file in your project root:

```env
# .env file
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_API_KEY=your-google-key

# Optional: Default model settings
DEFAULT_MODEL_PROVIDER=openai
DEFAULT_MODEL_NAME=gpt-4

# Memory and storage
MEMORY_BACKEND=local
VECTOR_STORE=chromadb
```

## Verification

Verify your installation:

```python
import buddy
print(f"Buddy AI version: {buddy.__version__}")

# Test basic agent creation
from buddy import Agent
from buddy.models.openai import OpenAIChat

# This will work if OpenAI is configured
try:
    agent = Agent(model=OpenAIChat())
    print("✅ Installation successful!")
except Exception as e:
    print(f"❌ Setup needed: {e}")
```

## Troubleshooting

### Common Issues

**Import Error: No module named 'openai'**
```bash
pip install buddy-ai[openai]
```

**Authentication Error**
- Verify your API keys are set correctly
- Check if keys have proper permissions
- Ensure environment variables are loaded

**Version Conflicts**
```bash
pip install --upgrade buddy-ai
```

### Getting Help

- [GitHub Issues](https://github.com/esasrir91/buddy-ai/issues)
- [Discussions](https://github.com/esasrir91/buddy-ai/discussions)
- Check the [Troubleshooting Guide](../troubleshooting/common-issues.md)

## Next Steps

- [Quick Start Guide](quickstart.md)
- [Configuration](configuration.md)
- [Basic Examples](examples.md)