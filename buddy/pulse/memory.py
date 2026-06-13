"""
PULSE Professional Memory — employee-specific memory layer.

ProfessionalMemory organises what the PULSE employee remembers into structured
namespaces: KT knowledge, colleague impressions, decisions taken, project context,
and general episodic memory.

Note: Memory v2 is a plain Python class (not a Pydantic BaseModel), so
ProfessionalMemory is also a plain Python class that composes a Memory v2
instance for episodic storage while adding typed employee-specific stores.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from buddy.memory.v2.memory import Memory


# ---------------------------------------------------------------------------
# Typed memory entries (Pydantic models for serialisation)
# ---------------------------------------------------------------------------

class KTMemoryEntry(BaseModel):
    """A record of a completed KT session stored in professional memory."""

    session_id: str
    session_name: str
    knowledge_giver: str
    domain: str
    key_concepts: List[str]
    mental_model: str
    confidence_score: float
    learned_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list)


class ColleagueMemoryEntry(BaseModel):
    """What the PULSE employee remembers about a specific colleague."""

    colleague_name: str
    role: str
    interactions: List[str] = Field(default_factory=list)
    preferences: List[str] = Field(default_factory=list)
    working_style: Optional[str] = None
    last_interaction: Optional[datetime] = None


class DecisionMemoryEntry(BaseModel):
    """A decision the employee participated in or was informed of."""

    decision: str
    context: str
    rationale: str
    decided_by: Optional[str] = None
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    outcome: Optional[str] = None


class ProjectMemoryEntry(BaseModel):
    """Context about a project the employee is involved with."""

    project_name: str
    description: str
    my_role: str
    key_stakeholders: List[str] = Field(default_factory=list)
    current_status: Optional[str] = None
    important_notes: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# ProfessionalMemory — plain Python class (composes Memory v2)
# ---------------------------------------------------------------------------

class ProfessionalMemory:
    """
    Employee-aware memory layer.

    Maintains typed stores for:
      - kt_knowledge    : completed KT sessions
      - colleagues      : known people and impressions
      - decisions       : decisions made or witnessed
      - projects        : project context and status

    Also holds an optional Memory v2 instance for episodic/LLM-driven memory.
    """

    def __init__(self, episodic_memory: Optional[Memory] = None) -> None:
        self.episodic: Optional[Memory] = episodic_memory
        self.kt_knowledge: List[KTMemoryEntry] = []
        self.colleagues: List[ColleagueMemoryEntry] = []
        self.decisions: List[DecisionMemoryEntry] = []
        self.projects: List[ProjectMemoryEntry] = []

    # ------------------------------------------------------------------ KT
    def store_kt(self, entry: KTMemoryEntry) -> None:
        """Add a completed KT session to professional memory."""
        self.kt_knowledge.append(entry)

    def recall_kt(self, domain: Optional[str] = None, tags: Optional[List[str]] = None) -> List[KTMemoryEntry]:
        """Retrieve KT memories, optionally filtered by domain or tags."""
        results: List[KTMemoryEntry] = self.kt_knowledge
        if domain:
            results = [e for e in results if domain.lower() in e.domain.lower()]
        if tags:
            tag_set = {t.lower() for t in tags}
            results = [e for e in results if tag_set.intersection({t.lower() for t in e.tags})]
        return sorted(results, key=lambda e: e.learned_at, reverse=True)

    def get_kt_domains(self) -> List[str]:
        """List all domains the employee has taken KT on."""
        return list({e.domain for e in self.kt_knowledge})

    # ------------------------------------------------------------ Colleagues
    def remember_colleague(self, entry: ColleagueMemoryEntry) -> None:
        existing = self._find_colleague(entry.colleague_name)
        if existing:
            existing.interactions.extend(entry.interactions)
            existing.last_interaction = datetime.utcnow()
        else:
            self.colleagues.append(entry)

    def recall_colleague(self, name: str) -> Optional[ColleagueMemoryEntry]:
        return self._find_colleague(name)

    def _find_colleague(self, name: str) -> Optional[ColleagueMemoryEntry]:
        name_lower = name.lower()
        for c in self.colleagues:
            if name_lower in c.colleague_name.lower():
                return c
        return None

    # ------------------------------------------------------------- Decisions
    def log_decision(self, entry: DecisionMemoryEntry) -> None:
        self.decisions.append(entry)

    def recall_decisions(self, context_keyword: Optional[str] = None) -> List[DecisionMemoryEntry]:
        if not context_keyword:
            return list(reversed(self.decisions))
        kw = context_keyword.lower()
        return [d for d in reversed(self.decisions) if kw in d.context.lower() or kw in d.decision.lower()]

    # -------------------------------------------------------------- Projects
    def update_project(self, entry: ProjectMemoryEntry) -> None:
        for i, p in enumerate(self.projects):
            if p.project_name.lower() == entry.project_name.lower():
                self.projects[i] = entry
                return
        self.projects.append(entry)

    def recall_project(self, name: str) -> Optional[ProjectMemoryEntry]:
        name_lower = name.lower()
        for p in self.projects:
            if name_lower in p.project_name.lower():
                return p
        return None

    # --------------------------------------------------------- Summary helper
    def professional_summary(self) -> Dict[str, Any]:
        """Returns a dict summary of current professional memory state."""
        return {
            "kt_sessions_completed": len(self.kt_knowledge),
            "kt_domains": self.get_kt_domains(),
            "colleagues_known": len(self.colleagues),
            "decisions_logged": len(self.decisions),
            "projects_tracked": [p.project_name for p in self.projects],
        }
