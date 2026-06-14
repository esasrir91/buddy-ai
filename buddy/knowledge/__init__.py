from buddy.knowledge.agent import AgentKnowledge

try:
    from buddy.knowledge.irag import irag
except Exception:
    irag = None  # type: ignore[misc, assignment]

# Temporarily comment out to avoid circular imports during testing
# from buddy.knowledge.irag import IRAGKnowledgeBase
# from buddy.knowledge.agentic_irag import AgenticIRAGKnowledgeBase

__all__ = [
    "AgentKnowledge",
    "irag",
    # "IRAGKnowledgeBase",
    # "AgenticIRAGKnowledgeBase",
]
