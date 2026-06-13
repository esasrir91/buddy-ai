"""
PULSE Identity Layer — defines who the virtual employee is.

EmployeeProfile  : The core identity card of a PULSE employee.
ColleagueBook    : Directory of known colleagues.
WorkingHours     : Availability windows per day.
WorkStyle        : Personality traits that shape communication.
"""
from __future__ import annotations

from datetime import time
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Department(str, Enum):
    ENGINEERING = "Engineering"
    PRODUCT = "Product"
    DESIGN = "Design"
    DATA = "Data"
    MARKETING = "Marketing"
    SALES = "Sales"
    OPERATIONS = "Operations"
    FINANCE = "Finance"
    HR = "HR"
    LEGAL = "Legal"
    CUSTOMER_SUCCESS = "Customer Success"
    OTHER = "Other"


class SeniorityLevel(str, Enum):
    INTERN = "Intern"
    JUNIOR = "Junior"
    MID = "Mid"
    SENIOR = "Senior"
    STAFF = "Staff"
    PRINCIPAL = "Principal"
    LEAD = "Lead"
    MANAGER = "Manager"
    DIRECTOR = "Director"
    VP = "VP"
    C_LEVEL = "C-Level"


class CommunicationStyle(str, Enum):
    FORMAL = "formal"
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CONCISE = "concise"
    DETAILED = "detailed"


class WorkMode(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    IN_OFFICE = "in-office"


# ---------------------------------------------------------------------------
# WorkingHours
# ---------------------------------------------------------------------------

class DaySchedule(BaseModel):
    """Availability window for a single weekday."""
    start: time = Field(default=time(9, 0), description="Work start time (local)")
    end: time = Field(default=time(18, 0), description="Work end time (local)")
    available: bool = Field(default=True)


class WorkingHours(BaseModel):
    """Weekly working-hours schedule for a PULSE employee."""

    monday: DaySchedule = Field(default_factory=DaySchedule)
    tuesday: DaySchedule = Field(default_factory=DaySchedule)
    wednesday: DaySchedule = Field(default_factory=DaySchedule)
    thursday: DaySchedule = Field(default_factory=DaySchedule)
    friday: DaySchedule = Field(default_factory=DaySchedule)
    saturday: DaySchedule = Field(default_factory=lambda: DaySchedule(available=False))
    sunday: DaySchedule = Field(default_factory=lambda: DaySchedule(available=False))

    def is_available_on(self, day: str) -> bool:
        """Check availability by weekday name (case-insensitive)."""
        schedule: Optional[DaySchedule] = getattr(self, day.lower(), None)
        return schedule.available if schedule else False

    @classmethod
    def standard_five_day(cls) -> "WorkingHours":
        """Mon–Fri 9–6, weekends off."""
        return cls()

    @classmethod
    def always_on(cls) -> "WorkingHours":
        """All 7 days, 00:00–23:59 — for 24/7 virtual employees."""
        all_day = DaySchedule(start=time(0, 0), end=time(23, 59), available=True)
        return cls(
            monday=all_day,
            tuesday=all_day,
            wednesday=all_day,
            thursday=all_day,
            friday=all_day,
            saturday=all_day,
            sunday=all_day,
        )


# ---------------------------------------------------------------------------
# WorkStyle
# ---------------------------------------------------------------------------

class WorkStyle(BaseModel):
    """Personality traits that shape how the PULSE employee communicates and behaves."""

    communication_style: CommunicationStyle = CommunicationStyle.PROFESSIONAL
    asks_clarifying_questions: bool = True
    proactively_shares_updates: bool = True
    prefers_async_communication: bool = False
    detail_oriented: bool = True
    initiative_level: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="How proactively the employee takes initiative (0=waits for instructions, 1=fully autonomous)",
    )
    empathy_level: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Warmth and empathy in communications",
    )
    custom_traits: List[str] = Field(
        default_factory=list,
        description="Additional personality traits in free-text form",
    )


# ---------------------------------------------------------------------------
# ColleagueRecord / ColleagueBook
# ---------------------------------------------------------------------------

class ColleagueRecord(BaseModel):
    """A record of a known colleague."""

    full_name: str
    role: str
    department: Optional[str] = None
    email: Optional[str] = None
    slack_handle: Optional[str] = None
    teams_handle: Optional[str] = None
    notes: Optional[str] = None
    relationship: Optional[str] = Field(
        default=None,
        description="e.g. 'manager', 'direct-report', 'peer', 'cross-functional partner'",
    )


class ColleagueBook(BaseModel):
    """Directory of colleagues known to a PULSE employee."""

    colleagues: List[ColleagueRecord] = Field(default_factory=list)

    def add(self, colleague: ColleagueRecord) -> None:
        self.colleagues.append(colleague)

    def find_by_name(self, name: str) -> Optional[ColleagueRecord]:
        name_lower = name.lower()
        for c in self.colleagues:
            if name_lower in c.full_name.lower():
                return c
        return None

    def find_by_role(self, role: str) -> List[ColleagueRecord]:
        role_lower = role.lower()
        return [c for c in self.colleagues if role_lower in c.role.lower()]

    def list_names(self) -> List[str]:
        return [c.full_name for c in self.colleagues]


# ---------------------------------------------------------------------------
# EmployeeProfile — the core identity card
# ---------------------------------------------------------------------------

class EmployeeProfile(BaseModel):
    """
    The identity card of a PULSE virtual employee.

    This is what gets injected into the system prompt to give the agent
    a stable, human-like professional identity.
    """

    # --- Core identity ---
    full_name: str = Field(..., description="Employee's full name, e.g. 'Priya Sharma'")
    role: str = Field(..., description="Job title, e.g. 'Senior Backend Engineer'")
    department: str = Field(default="Engineering")
    team: Optional[str] = Field(default=None, description="Sub-team, e.g. 'Payments Platform'")
    employee_id: Optional[str] = Field(default=None)
    seniority: SeniorityLevel = SeniorityLevel.SENIOR

    # --- Reporting / org structure ---
    reporting_to: Optional[str] = Field(default=None, description="Manager's name")
    direct_reports: List[str] = Field(default_factory=list)

    # --- Skills and domain ---
    skills: List[str] = Field(default_factory=list, description="Technical/domain skills")
    domain_expertise: List[str] = Field(
        default_factory=list,
        description="Business domains the employee understands, e.g. ['payments', 'compliance']",
    )

    # --- Location / time ---
    timezone: str = Field(default="UTC", description="IANA timezone, e.g. 'Asia/Kolkata'")
    location: Optional[str] = None
    work_mode: WorkMode = WorkMode.REMOTE
    working_hours: WorkingHours = Field(default_factory=WorkingHours.standard_five_day)

    # --- Communication ---
    email: Optional[str] = None
    slack_handle: Optional[str] = None
    teams_handle: Optional[str] = None
    work_style: WorkStyle = Field(default_factory=WorkStyle)

    # --- Context ---
    start_date: Optional[str] = Field(
        default=None, description="ISO date when employee joined, e.g. '2024-01-15'"
    )
    bio: Optional[str] = Field(
        default=None,
        description="Short professional bio used in introduction messages",
    )
    company_name: Optional[str] = None
    company_description: Optional[str] = None

    def build_system_prompt_section(self) -> str:
        """Returns a formatted identity block for injection into the agent system prompt."""
        lines = [
            f"You are {self.full_name}, a {self.role} at {self.company_name or 'the company'}.",
            f"Department: {self.department}" + (f" — {self.team}" if self.team else ""),
        ]
        if self.reporting_to:
            lines.append(f"You report to {self.reporting_to}.")
        if self.skills:
            lines.append(f"Your core skills: {', '.join(self.skills)}.")
        if self.domain_expertise:
            lines.append(f"Your domain expertise: {', '.join(self.domain_expertise)}.")
        lines.append(f"Your timezone is {self.timezone}.")
        if self.bio:
            lines.append(f"\n{self.bio}")
        comm = self.work_style.communication_style.value
        lines.append(f"\nCommunication style: {comm}. You are professional, helpful, and precise.")
        if self.work_style.asks_clarifying_questions:
            lines.append("You ask targeted clarifying questions when something is unclear.")
        if self.work_style.proactively_shares_updates:
            lines.append("You proactively share status updates and surface blockers early.")
        return "\n".join(lines)

    def build_introduction(self) -> str:
        """Returns a natural first-person introduction message."""
        intro = f"Hi! I'm {self.full_name}, {self.role}"
        if self.department:
            intro += f" in the {self.department} team"
        if self.company_name:
            intro += f" at {self.company_name}"
        intro += "."
        if self.reporting_to:
            intro += f" I report to {self.reporting_to}."
        if self.skills:
            intro += f" My expertise includes {', '.join(self.skills[:3])}"
            if len(self.skills) > 3:
                intro += f" and {len(self.skills) - 3} more areas"
            intro += "."
        intro += " Looking forward to working with you!"
        return intro
