"""
05_rag_with_irag.py — Retrieval-Augmented Generation using Buddy's built-in iRAG

iRAG is Buddy AI's custom RAG engine: spaCy NLP + TF-IDF + cosine similarity.
No external vector DB required.

Install:
    pip install buddy-ai
    python -m spacy download en_core_web_sm

Set your API key:
    export OPENAI_API_KEY=sk-...
"""

from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.knowledge.irag import IRAG
from buddy.knowledge.document.text import TextKnowledgeBase

knowledge = TextKnowledgeBase(
    texts=[
        "Buddy AI is a Python framework for building intelligent agents. "
        "It supports 35+ LLM providers including OpenAI, Anthropic, and Google.",
        "iRAG is Buddy AI's custom retrieval engine that uses spaCy for NLP, "
        "TF-IDF for term weighting, and cosine similarity for semantic matching. "
        "It requires no external vector database.",
        "Buddy AI supports multi-agent Teams where agents collaborate to complete tasks. "
        "Teams have a coordinator model that routes requests to specialist agents.",
        "The Workflow engine supports sequential, parallel, and conditional execution. "
        "Workflows can be defined in Python and deployed via FastAPI or the CLI.",
    ],
    irag=IRAG(),
)

agent = Agent(
    name="knowledge_agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    knowledge=knowledge,
    search_knowledge=True,
    instructions=[
        "Always search your knowledge base before answering.",
        "Cite the source when using retrieved information.",
    ],
    markdown=True,
)

if __name__ == "__main__":
    knowledge.load()
    agent.print_response("How does iRAG work in Buddy AI?")
    agent.print_response("What LLM providers does Buddy AI support?")
