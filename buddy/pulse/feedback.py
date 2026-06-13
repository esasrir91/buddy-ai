"""
PULSE Feedback & Growth Engine — tracks performance and drives continuous improvement.

FeedbackSystem      : Receives and stores feedback from colleagues.
PerformanceTracker  : Tracks KPIs and performance trends.
GrowthMetrics       : Aggregated growth view for the PULSE employee.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FeedbackSentiment(str, Enum):
    POSITIVE = "positive"
    CONSTRUCTIVE = "constructive"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class FeedbackCategory(str, Enum):
    COMMUNICATION = "communication"
    TECHNICAL = "technical"
    COLLABORATION = "collaboration"
    PROACTIVITY = "proactivity"
    QUALITY = "quality"
    SPEED = "speed"
    KNOWLEDGE = "knowledge"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class FeedbackEntry(BaseModel):
    """A single piece of feedback received by the PULSE employee."""

    feedback_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    given_by: str
    category: FeedbackCategory = FeedbackCategory.OTHER
    sentiment: FeedbackSentiment = FeedbackSentiment.NEUTRAL
    content: str
    action_taken: Optional[str] = None
    received_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list)

    def acknowledge(self, action: str) -> None:
        self.action_taken = action


class PerformanceSnapshot(BaseModel):
    """A point-in-time snapshot of performance metrics."""

    snapshot_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    period: str = Field(..., description="e.g. '2024-W01', '2024-01'")
    tasks_completed: int = 0
    tasks_on_time: int = 0
    meetings_attended: int = 0
    kt_sessions_completed: int = 0
    average_confidence_score: float = 0.0
    feedback_positive: int = 0
    feedback_constructive: int = 0
    blockers_raised: int = 0
    blockers_resolved: int = 0
    notes: Optional[str] = None
    recorded_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def on_time_rate(self) -> float:
        if self.tasks_completed == 0:
            return 0.0
        return self.tasks_completed and self.tasks_on_time / self.tasks_completed

    @property
    def blocker_resolution_rate(self) -> float:
        if self.blockers_raised == 0:
            return 1.0
        return self.blockers_resolved / self.blockers_raised


class GrowthMetrics(BaseModel):
    """Aggregated growth view showing the PULSE employee's development over time."""

    total_kt_sessions: int = 0
    domains_mastered: List[str] = Field(default_factory=list)
    average_kt_confidence: float = 0.0
    total_tasks_completed: int = 0
    total_meetings_processed: int = 0
    net_promoter_score: float = 0.0
    top_strengths: List[str] = Field(default_factory=list)
    areas_to_improve: List[str] = Field(default_factory=list)
    computed_at: datetime = Field(default_factory=datetime.utcnow)

    def format_summary(self) -> str:
        lines = [
            "## PULSE Employee Growth Summary",
            f"- KT Sessions: {self.total_kt_sessions} across {len(self.domains_mastered)} domains",
            f"- Avg KT Confidence: {self.average_kt_confidence:.0%}",
            f"- Tasks Completed: {self.total_tasks_completed}",
            f"- Meetings Processed: {self.total_meetings_processed}",
        ]
        if self.top_strengths:
            lines.append(f"- Strengths: {', '.join(self.top_strengths)}")
        if self.areas_to_improve:
            lines.append(f"- Areas to grow: {', '.join(self.areas_to_improve)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# FeedbackSystem
# ---------------------------------------------------------------------------

class FeedbackSystem:
    """Receives and organises feedback for the PULSE employee."""

    def __init__(self, employee_name: str) -> None:
        self.employee_name = employee_name
        self._feedback: List[FeedbackEntry] = []

    def receive(self, feedback: FeedbackEntry) -> None:
        self._feedback.append(feedback)

    def by_category(self, category: FeedbackCategory) -> List[FeedbackEntry]:
        return [f for f in self._feedback if f.category == category]

    def by_sentiment(self, sentiment: FeedbackSentiment) -> List[FeedbackEntry]:
        return [f for f in self._feedback if f.sentiment == sentiment]

    def recent(self, n: int = 5) -> List[FeedbackEntry]:
        return sorted(self._feedback, key=lambda f: f.received_at, reverse=True)[:n]

    def sentiment_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {s.value: 0 for s in FeedbackSentiment}
        for f in self._feedback:
            dist[f.sentiment.value] += 1
        return dist

    def actionable_items(self) -> List[FeedbackEntry]:
        """Returns constructive feedback items that have not yet been acted upon."""
        return [
            f for f in self._feedback
            if f.sentiment == FeedbackSentiment.CONSTRUCTIVE and not f.action_taken
        ]

    def build_improvement_prompt(self) -> str:
        """Returns a prompt snippet for self-improvement based on recent constructive feedback."""
        items = self.actionable_items()
        if not items:
            return ""
        feedback_text = "\n".join(f"- [{f.category.value}] {f.content}" for f in items[:5])
        return (
            f"Recent constructive feedback to incorporate into my behaviour:\n"
            f"{feedback_text}\n"
            f"I should actively work on addressing these points in my responses and actions."
        )


# ---------------------------------------------------------------------------
# PerformanceTracker
# ---------------------------------------------------------------------------

class PerformanceTracker:
    """Tracks performance metrics across time periods for the PULSE employee."""

    def __init__(self, employee_name: str) -> None:
        self.employee_name = employee_name
        self._snapshots: List[PerformanceSnapshot] = []

    def record(self, snapshot: PerformanceSnapshot) -> None:
        self._snapshots.append(snapshot)

    def latest(self) -> Optional[PerformanceSnapshot]:
        if not self._snapshots:
            return None
        return sorted(self._snapshots, key=lambda s: s.recorded_at, reverse=True)[0]

    def compute_growth_metrics(
        self,
        kt_sessions: int,
        domains: List[str],
        avg_confidence: float,
        tasks_done: int,
        meetings_done: int,
        feedback_system: Optional[FeedbackSystem] = None,
    ) -> GrowthMetrics:
        strengths: List[str] = []
        improvements: List[str] = []
        if feedback_system:
            dist = feedback_system.sentiment_distribution()
            positive = dist.get("positive", 0)
            constructive = dist.get("constructive", 0)
            total = positive + constructive
            nps = (positive / total * 100) if total > 0 else 0.0
            # Derive strengths from positive feedback categories
            for category in FeedbackCategory:
                pos = [f for f in feedback_system.by_category(category) if f.sentiment == FeedbackSentiment.POSITIVE]
                if pos:
                    strengths.append(category.value)
            for item in feedback_system.actionable_items()[:3]:
                improvements.append(item.category.value)
        else:
            nps = 0.0
        return GrowthMetrics(
            total_kt_sessions=kt_sessions,
            domains_mastered=domains,
            average_kt_confidence=avg_confidence,
            total_tasks_completed=tasks_done,
            total_meetings_processed=meetings_done,
            net_promoter_score=nps,
            top_strengths=strengths,
            areas_to_improve=improvements,
        )
