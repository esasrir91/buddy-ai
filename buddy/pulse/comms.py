"""
PULSE Communication Hub — wraps existing Buddy-AI communication tools.

CommunicationHub provides a unified interface for the PULSE employee to send
messages via Slack, Gmail, Microsoft Teams, or Zoom, using the existing
tool integrations in buddy/tools/.
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from buddy.pulse.employee import PulseEmployee


# ---------------------------------------------------------------------------
# Enums / Models
# ---------------------------------------------------------------------------

class CommChannel(str, Enum):
    SLACK = "slack"
    EMAIL = "email"
    TEAMS = "microsoft_teams"
    ZOOM = "zoom"
    INTERNAL = "internal"


class OutboundMessage(BaseModel):
    """A message composed and sent by the PULSE employee."""

    channel: CommChannel
    recipient: str
    subject: Optional[str] = None
    body: str
    sent: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageFormatter:
    """Formats messages to match the PULSE employee's work style."""

    def __init__(self, employee_name: str, communication_style: str = "professional") -> None:
        self.employee_name = employee_name
        self.style = communication_style

    def format_eod_summary(
        self,
        tasks_summary: str,
        blockers: List[str],
        tomorrow_plan: str,
    ) -> str:
        lines = [
            f"*EOD Update — {self.employee_name}*",
            "",
            "*What I worked on today:*",
            tasks_summary,
        ]
        if blockers:
            lines.append("\n*Blockers:*")
            for b in blockers:
                lines.append(f"• {b}")
        if tomorrow_plan:
            lines.append(f"\n*Tomorrow's plan:*\n{tomorrow_plan}")
        return "\n".join(lines)

    def format_clarification_request(self, task_title: str, question: str) -> str:
        return (
            f"Hi, I'm working on *{task_title}* and have a quick clarification needed:\n\n"
            f"{question}\n\n"
            f"Thanks!\n— {self.employee_name}"
        )

    def format_task_complete(self, task_title: str, summary: str) -> str:
        return (
            f"✅ *Task Complete: {task_title}*\n\n"
            f"{summary}\n\n"
            f"— {self.employee_name}"
        )


# ---------------------------------------------------------------------------
# CommunicationHub
# ---------------------------------------------------------------------------

class CommunicationHub:
    """
    Unified communication interface for the PULSE employee.

    Wraps existing Buddy-AI tool integrations. When a tool is not available
    (not installed / not configured), operations degrade gracefully and log
    a warning rather than raising.
    """

    def __init__(self, employee: "PulseEmployee") -> None:
        self.employee = employee
        self.formatter = MessageFormatter(
            employee_name=employee.employee_profile.full_name,
            communication_style=employee.employee_profile.work_style.communication_style.value,
        )
        self._outbox: List[OutboundMessage] = []
        self._slack_tool = self._load_tool("buddy.tools.slack", "SlackTools")
        self._gmail_tool = self._load_tool("buddy.tools.gmail", "GmailTools")
        self._teams_tool = self._load_tool("buddy.tools.ms_teams", "MicrosoftTeamsTools")
        self._zoom_tool = self._load_tool("buddy.tools.zoom", "ZoomTools")

    @staticmethod
    def _load_tool(module_path: str, class_name: str) -> Optional[Any]:
        try:
            import importlib
            mod = importlib.import_module(module_path)
            return getattr(mod, class_name)()
        except Exception:
            return None

    # ----------------------------------------------------------------- Slack
    def send_slack_message(self, channel_or_user: str, message: str) -> OutboundMessage:
        msg = OutboundMessage(channel=CommChannel.SLACK, recipient=channel_or_user, body=message)
        if self._slack_tool:
            try:
                self._slack_tool.send_message(channel=channel_or_user, message=message)  # type: ignore[attr-defined]
                msg.sent = True
            except Exception as e:
                msg.error = str(e)
        else:
            msg.error = "SlackTools not available — install buddy-ai[tools]"
        self._outbox.append(msg)
        return msg

    # ------------------------------------------------------------------ Email
    def send_email(self, to: str, subject: str, body: str) -> OutboundMessage:
        msg = OutboundMessage(channel=CommChannel.EMAIL, recipient=to, subject=subject, body=body)
        if self._gmail_tool:
            try:
                self._gmail_tool.send_email(to=to, subject=subject, body=body)  # type: ignore[attr-defined]
                msg.sent = True
            except Exception as e:
                msg.error = str(e)
        else:
            msg.error = "GmailTools not available — install buddy-ai[tools]"
        self._outbox.append(msg)
        return msg

    # --------------------------------------------------------------- Teams
    def send_teams_message(self, channel: str, message: str) -> OutboundMessage:
        msg = OutboundMessage(channel=CommChannel.TEAMS, recipient=channel, body=message)
        if self._teams_tool:
            try:
                self._teams_tool.send_message(channel=channel, message=message)  # type: ignore[attr-defined]
                msg.sent = True
            except Exception as e:
                msg.error = str(e)
        else:
            msg.error = "MicrosoftTeamsTools not available — install buddy-ai[tools]"
        self._outbox.append(msg)
        return msg

    # ----------------------------------------------------------- EOD Summary
    def send_eod_summary(
        self,
        channel: str,
        comm_channel: CommChannel = CommChannel.SLACK,
        tasks_summary: str = "",
        blockers: Optional[List[str]] = None,
        tomorrow_plan: str = "",
    ) -> OutboundMessage:
        body = self.formatter.format_eod_summary(
            tasks_summary=tasks_summary,
            blockers=blockers or [],
            tomorrow_plan=tomorrow_plan,
        )
        if comm_channel == CommChannel.SLACK:
            return self.send_slack_message(channel, body)
        elif comm_channel == CommChannel.EMAIL:
            return self.send_email(channel, f"EOD Update — {self.employee.employee_profile.full_name}", body)
        elif comm_channel == CommChannel.TEAMS:
            return self.send_teams_message(channel, body)
        msg = OutboundMessage(channel=comm_channel, recipient=channel, body=body, sent=False, error="Channel not supported")
        self._outbox.append(msg)
        return msg

    # --------------------------------------------------------- Message log
    @property
    def outbox(self) -> List[OutboundMessage]:
        return list(self._outbox)

    def sent_messages(self) -> List[OutboundMessage]:
        return [m for m in self._outbox if m.sent]
