from __future__ import annotations

from typing import List, Optional

from buddy.models.base import Model
from buddy.models.message import Message
from buddy.utils.log import logger


def _prepare_messages(messages: List[Message]) -> List[Message]:
    return [
        message.model_copy(update={"role": "system"}) if message.role == "developer" else message
        for message in messages
    ]


def _extract_reasoning_content(response_messages: Optional[List[Message]]) -> str:
    if response_messages:
        for message in response_messages:
            if message.reasoning_content is not None:
                return message.reasoning_content
    return ""


def is_deepseek_reasoning_model(reasoning_model: Model) -> bool:
    return reasoning_model.__class__.__name__ == "DeepSeek" and reasoning_model.id.lower() == "deepseek-reasoner"


def get_deepseek_reasoning(reasoning_agent: "Agent", messages: List[Message]) -> Optional[Message]:  # type: ignore  # noqa: F821
    from buddy.run.response import RunResponse

    try:
        reasoning_agent_response: RunResponse = reasoning_agent.run(messages=_prepare_messages(messages))
    except Exception as e:
        logger.warning(f"Reasoning error: {e}")
        return None

    reasoning_content = _extract_reasoning_content(reasoning_agent_response.messages)

    return Message(
        role="assistant", content=f"<thinking>\n{reasoning_content}\n</thinking>", reasoning_content=reasoning_content
    )


async def aget_deepseek_reasoning(reasoning_agent: "Agent", messages: List[Message]) -> Optional[Message]:  # type: ignore  # noqa: F821
    from buddy.run.response import RunResponse

    try:
        reasoning_agent_response: RunResponse = await reasoning_agent.arun(messages=_prepare_messages(messages))
    except Exception as e:
        logger.warning(f"Reasoning error: {e}")
        return None

    reasoning_content = _extract_reasoning_content(reasoning_agent_response.messages)

    return Message(
        role="assistant", content=f"<thinking>\n{reasoning_content}\n</thinking>", reasoning_content=reasoning_content
    )
