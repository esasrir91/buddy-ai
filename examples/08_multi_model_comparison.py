"""
08_multi_model_comparison.py — Run the same prompt across multiple LLM providers

Useful for benchmarking latency, quality, and cost across providers.

Install:
    pip install buddy-ai anthropic google-generativeai

Set API keys:
    export OPENAI_API_KEY=sk-...
    export ANTHROPIC_API_KEY=sk-ant-...
    export GOOGLE_API_KEY=AIza...
"""

import time
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.models.anthropic import Claude
from buddy.models.google import Gemini

PROMPT = "Explain the concept of entropy in 2 sentences."

MODELS = [
    ("OpenAI GPT-4o-mini", OpenAIChat(id="gpt-4o-mini")),
    ("Anthropic Claude Haiku", Claude(id="claude-haiku-20240307")),
    ("Google Gemini Flash", Gemini(id="gemini-1.5-flash")),
]

if __name__ == "__main__":
    for name, model in MODELS:
        agent = Agent(name=name, model=model)
        print(f"\n{'='*60}")
        print(f"Model: {name}")
        print(f"{'='*60}")
        start = time.perf_counter()
        agent.print_response(PROMPT)
        elapsed = time.perf_counter() - start
        print(f"\nLatency: {elapsed:.2f}s")
