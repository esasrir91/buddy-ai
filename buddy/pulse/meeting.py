"""
PULSE Meeting Intelligence — attend, process, and extract value from meetings.

MeetingParticipant  : Drives meeting processing for a PULSE employee.
MeetingNotes        : Structured output from a processed meeting.
ActionItem          : A task extracted from a meeting.
TranscriptProcessor : Parses raw transcripts into structured entries.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from buddy.pulse.employee import PulseEmployee


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MeetingPlatform(str, Enum):
    ZOOM = "zoom"
    TEAMS = "microsoft_teams"
    GOOGLE_MEET = "google_meet"
    SLACK_HUDDLE = "slack_huddle"
    IN_PERSON = "in_person"
    OTHER = "other"


class ActionItemPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionItemStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ActionItem(BaseModel):
    """A task extracted from a meeting transcript."""

    action_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    description: str
    owner: Optional[str] = None
    due_date: Optional[str] = None
    priority: ActionItemPriority = ActionItemPriority.MEDIUM
    status: ActionItemStatus = ActionItemStatus.OPEN
    source_meeting_id: Optional[str] = None

    def mark_done(self) -> None:
        self.status = ActionItemStatus.DONE

    def mark_in_progress(self) -> None:
        self.status = ActionItemStatus.IN_PROGRESS


class TranscriptEntry(BaseModel):
    """A single utterance in a meeting transcript."""

    speaker: str
    text: str
    timestamp: Optional[str] = None


class MeetingNotes(BaseModel):
    """Structured output from a PULSE-attended meeting."""

    meeting_id: str = Field(default_factory=lambda: str(uuid4()))
    title: Optional[str] = None
    platform: MeetingPlatform = MeetingPlatform.OTHER
    participants: List[str] = Field(default_factory=list)
    date: datetime = Field(default_factory=datetime.utcnow)

    summary: str = ""
    key_decisions: List[str] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    topics_discussed: List[str] = Field(default_factory=list)

    pulse_contributions: List[str] = Field(
        default_factory=list,
        description="Points/questions the PULSE employee contributed",
    )

    def my_action_items(self, employee_name: str) -> List[ActionItem]:
        name_lower = employee_name.lower()
        return [a for a in self.action_items if a.owner and name_lower in a.owner.lower()]

    def open_action_items(self) -> List[ActionItem]:
        return [a for a in self.action_items if a.status == ActionItemStatus.OPEN]

    def format_summary(self) -> str:
        lines = [f"## Meeting Notes — {self.title or 'Untitled'}"]
        lines.append(f"Date: {self.date.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"Participants: {', '.join(self.participants)}")
        lines.append(f"\n**Summary:** {self.summary}")
        if self.key_decisions:
            lines.append("\n**Key Decisions:**")
            for d in self.key_decisions:
                lines.append(f"- {d}")
        if self.action_items:
            lines.append("\n**Action Items:**")
            for a in self.action_items:
                owner = f" (@{a.owner})" if a.owner else ""
                due = f" — due {a.due_date}" if a.due_date else ""
                lines.append(f"- [{a.priority.value.upper()}] {a.description}{owner}{due}")
        if self.open_questions:
            lines.append("\n**Open Questions:**")
            for q in self.open_questions:
                lines.append(f"- {q}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# TranscriptProcessor
# ---------------------------------------------------------------------------

class TranscriptProcessor:
    """Parses a raw meeting transcript string into structured TranscriptEntry list."""

    @staticmethod
    def parse(raw_transcript: str) -> List[TranscriptEntry]:
        """
        Parses transcripts in the common formats:
          "SpeakerName: message text"
          "[HH:MM] SpeakerName: message text"
        """
        entries: List[TranscriptEntry] = []
        for line in raw_transcript.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            timestamp = None
            if line.startswith("["):
                bracket_end = line.find("]")
                if bracket_end != -1:
                    timestamp = line[1:bracket_end]
                    line = line[bracket_end + 1:].strip()
            if ":" in line:
                speaker, _, text = line.partition(":")
                entries.append(TranscriptEntry(
                    speaker=speaker.strip(),
                    text=text.strip(),
                    timestamp=timestamp,
                ))
            elif line:
                entries.append(TranscriptEntry(speaker="Unknown", text=line, timestamp=timestamp))
        return entries

    @staticmethod
    def extract_participants(entries: List[TranscriptEntry]) -> List[str]:
        seen: dict = {}
        for e in entries:
            if e.speaker not in seen:
                seen[e.speaker] = True
        return list(seen.keys())


# ---------------------------------------------------------------------------
# MeetingParticipant
# ---------------------------------------------------------------------------

class MeetingParticipant:
    """
    Manages meeting-related capabilities for a PULSE employee.

    Used internally by PulseEmployee — constructs the LLM prompt for processing
    a meeting transcript and returns structured MeetingNotes.
    """

    def __init__(self, employee: "PulseEmployee") -> None:
        self.employee = employee

    def build_processing_prompt(
        self,
        transcript: str,
        participants: List[str],
        platform: MeetingPlatform,
        title: Optional[str],
    ) -> str:
        name = self.employee.employee_profile.full_name
        role = self.employee.employee_profile.role
        participants_str = ", ".join(participants) if participants else "unknown participants"
        return f"""You are {name} ({role}). You have just attended a meeting on {platform.value}.

Participants: {participants_str}
{f'Meeting title: {title}' if title else ''}

Here is the meeting transcript:
---
{transcript}
---

Please produce a JSON response with the following fields:
{{
  "title": "<meeting title or 'Team Sync' if unknown>",
  "summary": "<2-3 sentence summary of what was discussed>",
  "key_decisions": ["<decision 1>", ...],
  "action_items": [
    {{"description": "...", "owner": "<name or null>", "due_date": "<YYYY-MM-DD or null>", "priority": "low|medium|high|critical"}}
  ],
  "open_questions": ["<question 1>", ...],
  "topics_discussed": ["<topic 1>", ...],
  "pulse_contributions": ["<points {name} could contribute based on their expertise>"]
}}

Be precise and extract only what is explicitly mentioned in the transcript."""

    def create_notes_from_dict(
        self,
        data: dict,
        participants: List[str],
        platform: MeetingPlatform,
        meeting_id: str,
    ) -> MeetingNotes:
        action_items = [
            ActionItem(
                description=a.get("description", ""),
                owner=a.get("owner"),
                due_date=a.get("due_date"),
                priority=ActionItemPriority(a.get("priority", "medium")),
                source_meeting_id=meeting_id,
            )
            for a in data.get("action_items", [])
        ]
        return MeetingNotes(
            meeting_id=meeting_id,
            title=data.get("title"),
            platform=platform,
            participants=participants,
            summary=data.get("summary", ""),
            key_decisions=data.get("key_decisions", []),
            action_items=action_items,
            open_questions=data.get("open_questions", []),
            topics_discussed=data.get("topics_discussed", []),
            pulse_contributions=data.get("pulse_contributions", []),
        )
