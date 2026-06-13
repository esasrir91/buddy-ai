"""
PULSE — Virtual Employee's ERA

The PULSE module turns a Buddy-AI Agent into a fully-functional virtual human
team member. Import the key classes from here:

    from buddy.pulse import PulseEmployee, EmployeeProfile, KTSourceType

See the full documentation at docs/advanced/pulse.md
"""
from buddy.pulse.employee import PulseEmployee
from buddy.pulse.feedback import (
    FeedbackCategory,
    FeedbackEntry,
    FeedbackSentiment,
    FeedbackSystem,
    GrowthMetrics,
    PerformanceSnapshot,
    PerformanceTracker,
)
from buddy.pulse.identity import (
    ColleagueBook,
    ColleagueRecord,
    CommunicationStyle,
    Department,
    EmployeeProfile,
    SeniorityLevel,
    WorkingHours,
    WorkMode,
    WorkStyle,
)
from buddy.pulse.kt import (
    KTManager,
    KTPhase,
    KTSession,
    KTSessionState,
    KTSourceType,
    KTSummary,
    KTTurn,
)
from buddy.pulse.meeting import (
    ActionItem,
    ActionItemPriority,
    ActionItemStatus,
    MeetingNotes,
    MeetingParticipant,
    MeetingPlatform,
    TranscriptProcessor,
    TranscriptEntry,
)
from buddy.pulse.memory import (
    ColleagueMemoryEntry,
    DecisionMemoryEntry,
    KTMemoryEntry,
    ProjectMemoryEntry,
    ProfessionalMemory,
)
from buddy.pulse.onboarding import OnboardingConfig, OnboardingResult, OnboardingWorkflow
from buddy.pulse.work import (
    CalendarEvent,
    StatusUpdate,
    TaskManager,
    TaskPriority,
    TaskStatus,
    TaskType,
    WorkCalendar,
    WorkItem,
)

__all__ = [
    # Core employee
    "PulseEmployee",
    # Identity
    "EmployeeProfile",
    "ColleagueBook",
    "ColleagueRecord",
    "WorkingHours",
    "WorkStyle",
    "WorkMode",
    "CommunicationStyle",
    "Department",
    "SeniorityLevel",
    # KT
    "KTSession",
    "KTManager",
    "KTSourceType",
    "KTSummary",
    "KTTurn",
    "KTPhase",
    "KTSessionState",
    # Meeting
    "MeetingNotes",
    "MeetingParticipant",
    "MeetingPlatform",
    "ActionItem",
    "ActionItemPriority",
    "ActionItemStatus",
    "TranscriptProcessor",
    "TranscriptEntry",
    # Memory
    "ProfessionalMemory",
    "KTMemoryEntry",
    "ColleagueMemoryEntry",
    "DecisionMemoryEntry",
    "ProjectMemoryEntry",
    # Work
    "WorkItem",
    "TaskManager",
    "WorkCalendar",
    "CalendarEvent",
    "StatusUpdate",
    "TaskPriority",
    "TaskStatus",
    "TaskType",
    # Feedback
    "FeedbackEntry",
    "FeedbackSystem",
    "FeedbackCategory",
    "FeedbackSentiment",
    "PerformanceTracker",
    "PerformanceSnapshot",
    "GrowthMetrics",
    # Onboarding
    "OnboardingWorkflow",
    "OnboardingConfig",
    "OnboardingResult",
]
