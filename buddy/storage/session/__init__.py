from typing import Union

from buddy.storage.session.agent import AgentSession
from buddy.storage.session.team import TeamSession
from buddy.storage.session.v2.workflow import WorkflowSession as WorkflowSessionV2
from buddy.storage.session.workflow import WorkflowSession

Session = Union[AgentSession, TeamSession, WorkflowSession, WorkflowSessionV2]

__all__ = [
    "AgentSession",
    "TeamSession",
    "WorkflowSession",
    "WorkflowSessionV2",
    "Session",
]

