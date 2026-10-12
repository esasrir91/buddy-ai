from __future__ import annotations

from typing import List, Optional

from buddy.models.base import Model
from buddy.models.message import Message
from buddy.utils.log import logger


def _extract_reasoning_content(content: Optional[str]) -> str:
    if content is None:
        return ""

    start_tag = "<think>"
    end_tag = "</think>"
    start_idx = content.find(start_tag)
    if start_idx == -1:
        return content

    end_idx = content.find(end_tag, start_idx + len(start_tag))
    if end_idx == -1:
        return content

    return content[start_idx + len(start_tag) : end_idx].strip()


def is_ai_foundry_reasoning_model(reasoning_model: Model) -> bool:
    return reasoning_model.__class__.__name__ == "AzureAIFoundry" and (
        ("deepseek" in reasoning_model.id.lower())
        or ("o1" in reasoning_model.id.lower())
        or ("o3" in reasoning_model.id.lower())
        or ("o4" in reasoning_model.id.lower())
    )


def get_ai_foundry_reasoning(reasoning_agent: "Agent", messages: List[Message]) -> Optional[Message]:  # type: ignore  # noqa: F821
    from buddy.run.response import RunResponse

    try:
        reasoning_agent_response: RunResponse = reasoning_agent.run(messages=messages)
    except Exception as e:
        logger.warning(f"Reasoning error: {e}")
        return None

    # Azure AI Foundry does not expose a separate reasoning field.
    reasoning_content = _extract_reasoning_content(reasoning_agent_response.content)

    return Message(
        role="assistant", content=f"<thinking>\n{reasoning_content}\n</thinking>", reasoning_content=reasoning_content
    )


async def aget_ai_foundry_reasoning(reasoning_agent: "Agent", messages: List[Message]) -> Optional[Message]:  # type: ignore  # noqa: F821
    from buddy.run.response import RunResponse

    try:
        reasoning_agent_response: RunResponse = await reasoning_agent.arun(messages=messages)
    except Exception as e:
        logger.warning(f"Reasoning error: {e}")
        return None

    reasoning_content = _extract_reasoning_content(reasoning_agent_response.content)

    return Message(
        role="assistant", content=f"<thinking>\n{reasoning_content}\n</thinking>", reasoning_content=reasoning_content
    )
