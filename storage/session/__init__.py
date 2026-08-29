from typing import Union

from buddy.storage.session.agent import AgentSession
from buddy.storage.session.team import TeamSession
from buddy.storage.session.workflow import WorkflowSession

Session = Union[AgentSession, TeamSession, WorkflowSession]

__all__ = [
    "AgentSession",
    "TeamSession",
    "WorkflowSession",
    "Session",
]
