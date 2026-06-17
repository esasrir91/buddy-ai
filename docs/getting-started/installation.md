# Installation

## Requirements

- Python **3.10** or newer
- pip 23+

## Basic Install

```bash
pip install buddy-ai
```

This installs the core framework with OpenAI support, iRAG, FastAPI, Streamlit, and the CLI.

## Optional Extras

Install only what you need:

```bash
# Local model fine-tuning (PyTorch + HuggingFace)
pip install "buddy-ai[training]"

# Multi-modal vision, audio, and video processing
pip install "buddy-ai[multimodal]"

# Popular tool SDK dependencies
pip install "buddy-ai[tools]"

# Additional LLM providers
pip install "buddy-ai[anthropic]"
pip install "buddy-ai[google]"
pip install "buddy-ai[cohere]"
pip install "buddy-ai[aws]"

# Ecosystem integrations
pip install "buddy-ai[langchain]"   # use Buddy in LangChain
pip install "buddy-ai[langgraph]"   # run Buddy agents as LangGraph nodes

# Everything at once
pip install "buddy-ai[all]"

# Development (testing, linting, type checking)
pip install "buddy-ai[dev]"
```

## Verify Installation

```python
import buddy
print(buddy.__version__)       # e.g. 2.2.0
print(buddy.get_version_info())
```

Or via the CLI:

```bash
buddy --version
```

## Environment Variables

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

At minimum, set one LLM provider key:

```bash
export OPENAI_API_KEY=sk-...
# or
export ANTHROPIC_API_KEY=sk-ant-...
```

## Upgrading

```bash
pip install --upgrade buddy-ai
```
