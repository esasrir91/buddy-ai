"""
PULSE Employee — the main virtual employee class.

PulseEmployee extends Agent with a full professional identity, KT capabilities,
meeting intelligence, task management, and proactive communication — making it
behave like a real human team member.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from buddy.agent import Agent
from buddy.pulse.comms import CommChannel, CommunicationHub
from buddy.pulse.feedback import (
    FeedbackCategory,
    FeedbackEntry,
    FeedbackSentiment,
    FeedbackSystem,
    PerformanceTracker,
)
from buddy.pulse.identity import EmployeeProfile
from buddy.pulse.kt import KTManager, KTSession, KTSourceType, KTSummary
from buddy.pulse.meeting import (
    MeetingNotes,
    MeetingParticipant,
    MeetingPlatform,
    TranscriptProcessor,
)
from buddy.pulse.memory import (
    ColleagueMemoryEntry,
    KTMemoryEntry,
    ProfessionalMemory,
)
from buddy.pulse.work import StatusUpdate, TaskManager, TaskPriority, WorkCalendar, WorkItem


class PulseEmployee(Agent):
    """
    A virtual employee powered by Buddy AI.

    Extends Agent with:
      - EmployeeProfile  : stable human-like identity
      - KTManager        : learns from documents and live human explanations
      - ProfessionalMemory: structured employee-aware memory
      - MeetingParticipant: attends and processes meetings
      - TaskManager      : receives and executes work items
      - CommunicationHub : sends Slack / email / Teams messages
      - FeedbackSystem   : receives and learns from feedback

    Quickstart:
        from buddy.pulse import PulseEmployee, EmployeeProfile
        from buddy.models.openai import OpenAIChat

        pulse = PulseEmployee(
            employee_profile=EmployeeProfile(
                full_name="Priya Sharma",
                role="Backend Engineer",
                department="Engineering",
                skills=["Python", "FastAPI", "PostgreSQL"],
            ),
            model=OpenAIChat(id="gpt-4o"),
        )
        pulse.introduce_yourself()
    """

    def __init__(
        self,
        employee_profile: EmployeeProfile,
        professional_memory: Optional[ProfessionalMemory] = None,
        **agent_kwargs: Any,
    ) -> None:
        # Build the system prompt from identity + any existing instructions
        existing_instructions = agent_kwargs.pop("instructions", []) or []
        if isinstance(existing_instructions, str):
            existing_instructions = [existing_instructions]

        identity_section = employee_profile.build_system_prompt_section()
        instructions = [identity_section] + list(existing_instructions)

        super().__init__(
            name=employee_profile.full_name,
            description=f"{employee_profile.role} at {employee_profile.company_name or 'the company'}",
            instructions=instructions,
            **agent_kwargs,
        )

        # --- Core identity ---
        self.employee_profile = employee_profile

        # --- Professional memory (use passed-in or create default) ---
        self.professional_memory: ProfessionalMemory = professional_memory or ProfessionalMemory()

        # --- Sub-systems (lazy-init via properties) ---
        self._kt_manager: Optional[KTManager] = None
        self._task_manager: Optional[TaskManager] = None
        self._work_calendar: Optional[WorkCalendar] = None
        self._meeting_participant: Optional[MeetingParticipant] = None
        self._communication_hub: Optional[CommunicationHub] = None
        self._feedback_system: Optional[FeedbackSystem] = None
        self._performance_tracker: Optional[PerformanceTracker] = None

    # ---------------------------------------------------------------- Properties
    @property
    def kt_manager(self) -> KTManager:
        if self._kt_manager is None:
            self._kt_manager = KTManager(self)
        return self._kt_manager

    @property
    def task_manager(self) -> TaskManager:
        if self._task_manager is None:
            self._task_manager = TaskManager(self.employee_profile.full_name)
        return self._task_manager

    @property
    def work_calendar(self) -> WorkCalendar:
        if self._work_calendar is None:
            self._work_calendar = WorkCalendar()
        return self._work_calendar

    @property
    def meeting_participant(self) -> MeetingParticipant:
        if self._meeting_participant is None:
            self._meeting_participant = MeetingParticipant(self)
        return self._meeting_participant

    @property
    def communication_hub(self) -> CommunicationHub:
        if self._communication_hub is None:
            self._communication_hub = CommunicationHub(self)
        return self._communication_hub

    @property
    def feedback_system(self) -> FeedbackSystem:
        if self._feedback_system is None:
            self._feedback_system = FeedbackSystem(self.employee_profile.full_name)
        return self._feedback_system

    @property
    def performance_tracker(self) -> PerformanceTracker:
        if self._performance_tracker is None:
            self._performance_tracker = PerformanceTracker(self.employee_profile.full_name)
        return self._performance_tracker

    # ==========================================================================
    # IDENTITY
    # ==========================================================================

    def introduce_yourself(self) -> str:
        """Returns a natural first-person introduction message."""
        return self.employee_profile.build_introduction()

    def my_profile(self) -> Dict[str, Any]:
        """Returns a dict summary of the employee's profile."""
        p = self.employee_profile
        return {
            "name": p.full_name,
            "role": p.role,
            "department": p.department,
            "team": p.team,
            "skills": p.skills,
            "timezone": p.timezone,
            "reporting_to": p.reporting_to,
        }

    # ==========================================================================
    # KNOWLEDGE TRANSFER (KT)
    # ==========================================================================

    def take_kt(
        self,
        source: Union[str, bytes],
        source_type: KTSourceType,
        session_name: str,
        knowledge_giver: str,
        confidence_threshold: float = KTSession.CONFIDENCE_THRESHOLD,
    ) -> KTSummary:
        """
        Perform an async KT from a document, URL, or transcript.

        Args:
            source          : File path, URL string, or raw bytes.
            source_type     : Type of source (must be an async/non-HUMAN_ type).
            session_name    : Descriptive name for this KT session.
            knowledge_giver : Name of the person who provided the material.
            confidence_threshold: Minimum confidence score to accept (default 0.82).

        Returns:
            KTSummary with mental model, key concepts, open questions.
        """
        if source_type.is_human_mode:
            raise ValueError(
                f"source_type {source_type.value!r} is a live/human mode. "
                "Use start_live_kt() for interactive KT sessions."
            )
        session = self.kt_manager.create_session(
            session_name=session_name,
            source_type=source_type,
            knowledge_giver=knowledge_giver,
            confidence_threshold=confidence_threshold,
        )
        session.ingest(source)
        summary = session.generate_summary()
        session.commit()
        self.kt_manager.commit_summary(summary)
        self._store_kt_in_memory(summary)
        return summary

    def start_live_kt(
        self,
        session_name: str,
        knowledge_giver: str,
        source_type: KTSourceType = KTSourceType.HUMAN_CHAT,
        confidence_threshold: float = KTSession.CONFIDENCE_THRESHOLD,
        max_rounds: int = KTSession.MAX_ROUNDS,
    ) -> KTSession:
        """
        Start an interactive live KT session with a human knowledge-giver.

        Returns an open KTSession. The caller drives the conversation by calling:
            session.human_explains(...)
            session.human_answers({...})
            session.human_corrects(...)
            summary = session.generate_summary()
            session.commit()

        After commit(), call pulse.finalize_kt_session(session) to store the
        summary into professional memory.
        """
        if not source_type.is_human_mode:
            raise ValueError(
                f"source_type {source_type.value!r} is an async mode. " "Use take_kt() for document-based KT."
            )
        return self.kt_manager.create_session(
            session_name=session_name,
            source_type=source_type,
            knowledge_giver=knowledge_giver,
            confidence_threshold=confidence_threshold,
            max_rounds=max_rounds,
        )

    def finalize_kt_session(self, session: KTSession) -> KTSummary:
        """
        Generate summary, commit, and store a live KT session into memory.
        Call this after the human conversation is complete.
        """
        summary = session.generate_summary()
        session.commit()
        self.kt_manager.commit_summary(summary)
        self._store_kt_in_memory(summary)
        return summary

    def _store_kt_in_memory(self, summary: KTSummary) -> None:
        entry = KTMemoryEntry(
            session_id=summary.session_id,
            session_name=summary.session_name,
            knowledge_giver=summary.knowledge_giver,
            domain=summary.domain or summary.session_name,
            key_concepts=summary.key_concepts,
            mental_model=summary.mental_model,
            confidence_score=summary.confidence_score,
            tags=summary.tags,
        )
        self.professional_memory.store_kt(entry)

    def what_do_i_know_about(self, topic: str) -> str:
        """
        Introspect: returns a natural-language summary of what PULSE knows
        about a given topic, drawing from KT memories.
        """
        relevant = self.kt_manager.search_knowledge(topic)
        if not relevant:
            return f"I don't have specific KT knowledge about '{topic}' yet. I should take a KT on it!"

        summaries = "\n\n".join(
            f"From '{s.session_name}' (confidence: {s.confidence_score:.0%}):\n{s.mental_model}" for s in relevant[:3]
        )
        prompt = (
            f"I was asked: what do you know about '{topic}'?\n\n"
            f"Here is what I learned from KT sessions:\n{summaries}\n\n"
            f"Answer in first person, naturally, as {self.employee_profile.full_name}."
        )
        response = self.run(prompt, stream=False)
        if hasattr(response, "content") and response.content is not None:
            return str(response.content)
        return str(response)

    # ==========================================================================
    # MEETINGS
    # ==========================================================================

    def attend_meeting(
        self,
        transcript: str,
        participants: Optional[List[str]] = None,
        platform: MeetingPlatform = MeetingPlatform.OTHER,
        title: Optional[str] = None,
    ) -> MeetingNotes:
        """
        Process a meeting transcript and return structured MeetingNotes.

        Args:
            transcript  : Raw meeting transcript text.
            participants: List of participant names (auto-detected if None).
            platform    : Meeting platform enum.
            title       : Optional meeting title.

        Returns:
            MeetingNotes with summary, action items, decisions, open questions.
        """
        processor = TranscriptProcessor()
        entries = processor.parse(transcript)
        if not participants:
            participants = processor.extract_participants(entries)

        meeting_id = str(uuid4())
        prompt = self.meeting_participant.build_processing_prompt(
            transcript=transcript,
            participants=participants,
            platform=platform,
            title=title,
        )
        response = self.run(prompt, stream=False)
        raw = str(response.content) if hasattr(response, "content") and response.content is not None else str(response)
        data = KTSession._parse_json(raw)
        notes = self.meeting_participant.create_notes_from_dict(
            data=data,
            participants=participants,
            platform=platform,
            meeting_id=meeting_id,
        )
        # Auto-register my action items as work items
        for action in notes.my_action_items(self.employee_profile.full_name):
            self.task_manager.assign(
                WorkItem(
                    title=action.description,
                    description=f"Action item from meeting: {notes.title or meeting_id}",
                    assigned_by=f"Meeting: {notes.title or meeting_id}",
                    priority=TaskPriority(action.priority.value),
                    deadline=action.due_date,
                    tags=["meeting_action_item"],
                )
            )
        return notes

    # ==========================================================================
    # TASKS
    # ==========================================================================

    def receive_task(
        self,
        description: str,
        assigned_by: Optional[str] = None,
        priority: str = "medium",
        deadline: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> WorkItem:
        """Receive a new work item and register it in the task manager."""
        task = WorkItem(
            title=title or description[:60],
            description=description,
            assigned_by=assigned_by,
            assigned_to=self.employee_profile.full_name,
            priority=TaskPriority(priority.lower()),
            deadline=deadline,
            tags=tags or [],
        )
        return self.task_manager.assign(task)

    def report_status(self, task_id: Optional[str] = None) -> StatusUpdate:
        """
        Generate a status update for a specific task, or a general EOD-style
        summary of all active work if no task_id is given.
        """
        if task_id:
            task = self.task_manager.get(task_id)
            if not task:
                return StatusUpdate(
                    employee_name=self.employee_profile.full_name,
                    update_type="task_update",
                    message=f"Task {task_id!r} not found in my task list.",
                )
            context = f"Task: {task.title}\nStatus: {task.status.value}\n" + "\n".join(task.progress_notes)
        else:
            context = self.task_manager.build_eod_context()

        prompt = (
            f"You are {self.employee_profile.full_name} ({self.employee_profile.role}).\n\n"
            f"{context}\n\n"
            "Write a concise status update in JSON:\n"
            "{\n"
            '  "what_i_did": ["<item>", ...],\n'
            '  "what_i_will_do": ["<item>", ...],\n'
            '  "blockers": ["<item>", ...],\n'
            '  "percentage_complete": <0-100 or null>,\n'
            '  "message": "<optional additional note>"\n'
            "}"
        )
        response = self.run(prompt, stream=False)
        raw = str(response.content) if hasattr(response, "content") and response.content is not None else str(response)
        data = KTSession._parse_json(raw)
        task_title = task.title if task_id and task else None
        return StatusUpdate(
            employee_name=self.employee_profile.full_name,
            update_type="task_update" if task_id else "eod_summary",
            task_id=task_id,
            task_title=task_title,
            what_i_did=data.get("what_i_did", []),
            what_i_will_do=data.get("what_i_will_do", []),
            blockers=data.get("blockers", []),
            percentage_complete=data.get("percentage_complete"),
            message=data.get("message", ""),
        )

    def ask_for_clarification(self, task_title: str, question: str) -> str:
        """Returns a naturally-worded clarification request message."""
        return self.communication_hub.formatter.format_clarification_request(task_title, question)

    # ==========================================================================
    # FEEDBACK & GROWTH
    # ==========================================================================

    def receive_feedback(
        self,
        content: str,
        given_by: str,
        category: str = "other",
        sentiment: str = "neutral",
    ) -> FeedbackEntry:
        """Record feedback received from a colleague."""
        entry = FeedbackEntry(
            given_by=given_by,
            category=FeedbackCategory(category),
            sentiment=FeedbackSentiment(sentiment),
            content=content,
        )
        self.feedback_system.receive(entry)
        # Append constructive feedback as an instruction so PULSE improves
        if entry.sentiment == FeedbackSentiment.CONSTRUCTIVE:
            improvement_prompt = self.feedback_system.build_improvement_prompt()
            if improvement_prompt:
                if isinstance(self.instructions, list):
                    self.instructions.append(improvement_prompt)
        return entry

    # ==========================================================================
    # COMMUNICATION
    # ==========================================================================

    def send_eod_summary(
        self,
        channel: Optional[str] = None,
        comm_channel: CommChannel = CommChannel.SLACK,
    ) -> None:
        """Generate and send an end-of-day summary to the configured channel."""
        status = self.report_status()
        eod_channel = channel or self.employee_profile.slack_handle or "general"
        self.communication_hub.send_eod_summary(
            channel=eod_channel,
            comm_channel=comm_channel,
            tasks_summary="\n".join(f"• {item}" for item in status.what_i_did),
            blockers=status.blockers,
            tomorrow_plan="\n".join(f"• {item}" for item in status.what_i_will_do),
        )

    # ==========================================================================
    # ONBOARDING
    # ==========================================================================

    def run_onboarding(
        self,
        company_docs: Optional[List[str]] = None,
        team_members: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Run the onboarding workflow:
        1. Ingest company documents via KT.
        2. Register team members in colleague memory.
        3. Return onboarding result.
        """
        result: Dict[str, Any] = {"kt_completed": [], "colleagues_added": []}
        if company_docs:
            for doc_path in company_docs:
                try:
                    summary = self.take_kt(
                        source=doc_path,
                        source_type=KTSourceType.DOCUMENT,
                        session_name=f"Onboarding — {doc_path.split('/')[-1]}",
                        knowledge_giver="Onboarding Documents",
                    )
                    result["kt_completed"].append(summary.session_name)
                except Exception as e:
                    result["kt_completed"].append(f"FAILED: {doc_path} ({e})")

        if team_members:
            for member in team_members:
                entry = ColleagueMemoryEntry(
                    colleague_name=member.get("name", "Unknown"),
                    role=member.get("role", ""),
                    interactions=["Met during onboarding"],
                )
                self.professional_memory.remember_colleague(entry)
                result["colleagues_added"].append(entry.colleague_name)

        result["introduction"] = self.introduce_yourself()
        result["onboarded_at"] = datetime.utcnow().isoformat()
        return result
