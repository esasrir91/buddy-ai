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


def is_ollama_reasoning_model(reasoning_model: Model) -> bool:
    model_id = reasoning_model.id.lower()
    return reasoning_model.__class__.__name__ == "Ollama" and (
        "qwq" in model_id
        or "deepseek-r1" in model_id
        or "qwen2.5-coder" in model_id
        or "openthinker" in model_id
    )


def get_ollama_reasoning(reasoning_agent: "Agent", messages: List[Message]) -> Optional[Message]:  # type: ignore  # noqa: F821
    from buddy.run.response import RunResponse

    try:
        reasoning_agent_response: RunResponse = reasoning_agent.run(messages=messages)
    except Exception as e:
        logger.warning(f"Reasoning error: {e}")
        return None

    reasoning_content = _extract_reasoning_content(reasoning_agent_response.content)

    return Message(
        role="assistant", content=f"<thinking>\n{reasoning_content}\n</thinking>", reasoning_content=reasoning_content
    )


async def aget_ollama_reasoning(reasoning_agent: "Agent", messages: List[Message]) -> Optional[Message]:  # type: ignore  # noqa: F821
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
