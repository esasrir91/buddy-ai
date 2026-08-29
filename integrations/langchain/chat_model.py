"""Wrap a Buddy model as a LangChain ``BaseChatModel``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from buddy.integrations._utils import require
from buddy.integrations.langchain.messages import to_buddy_messages

if TYPE_CHECKING:  # pragma: no cover - typing only
    from langchain_core.callbacks import (
        AsyncCallbackManagerForLLMRun,
        CallbackManagerForLLMRun,
    )
    from langchain_core.messages import BaseMessage
    from langchain_core.outputs import ChatResult

    from buddy.models.base import Model


def _build_chat_model_class() -> type:
    """Construct the ``BuddyChatModel`` class against the installed LangChain.

    LangChain's ``BaseChatModel`` is a pydantic model, so the subclass must be
    declared after LangChain is importable. We build it lazily inside a factory
    and cache the result on the module.
    """
    require("langchain_core", "langchain")

    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult

    class _BuddyChatModel(BaseChatModel):
        """A LangChain chat model backed by any ``buddy.models`` model.

        This bridges Buddy's unified provider layer (OpenAI, Anthropic, Google,
        Cohere, AWS, Azure, Ollama, Groq, ...) into LangChain, so a single Buddy
        model object can drive LangChain chains, agents, and LangGraph nodes.

        Example:
            >>> from buddy.models.openai import OpenAIChat
            >>> from buddy.integrations.langchain import BuddyChatModel
            >>> llm = BuddyChatModel(buddy_model=OpenAIChat(id="gpt-4o-mini"))
            >>> llm.invoke("Say hello in French.")
        """

        buddy_model: Any = None

        model_config = {"arbitrary_types_allowed": True}

        @property
        def _llm_type(self) -> str:
            return "buddy"

        @property
        def _identifying_params(self) -> Dict[str, Any]:
            model = self.buddy_model
            return {
                "buddy_model_id": getattr(model, "id", None),
                "buddy_provider": getattr(model, "provider", None),
            }

        def _generate(
            self,
            messages: List["BaseMessage"],
            stop: Optional[List[str]] = None,
            run_manager: Optional["CallbackManagerForLLMRun"] = None,
            **kwargs: Any,
        ) -> "ChatResult":
            buddy_messages = to_buddy_messages(messages)
            model_response = self.buddy_model.response(messages=buddy_messages)
            return self._to_chat_result(model_response)

        async def _agenerate(
            self,
            messages: List["BaseMessage"],
            stop: Optional[List[str]] = None,
            run_manager: Optional["AsyncCallbackManagerForLLMRun"] = None,
            **kwargs: Any,
        ) -> "ChatResult":
            buddy_messages = to_buddy_messages(messages)
            model_response = await self.buddy_model.aresponse(messages=buddy_messages)
            return self._to_chat_result(model_response)

        @staticmethod
        def _to_chat_result(model_response: Any) -> "ChatResult":
            content = getattr(model_response, "content", None) or ""
            message = AIMessage(content=content)
            generation = ChatGeneration(message=message)
            return ChatResult(generations=[generation])

    _BuddyChatModel.__name__ = "BuddyChatModel"
    _BuddyChatModel.__qualname__ = "BuddyChatModel"
    return _BuddyChatModel


class _BuddyChatModelFactory:
    """Callable proxy that materializes the real class on first construction.

    Importing this module must not require LangChain, so ``BuddyChatModel`` is a
    lightweight proxy. The first call (or ``isinstance`` via the real class)
    triggers the actual subclass construction.
    """

    _cls: Optional[type] = None

    def _resolve(self) -> type:
        if _BuddyChatModelFactory._cls is None:
            _BuddyChatModelFactory._cls = _build_chat_model_class()
        return _BuddyChatModelFactory._cls

    def __call__(self, buddy_model: "Model" = None, **kwargs: Any) -> Any:
        cls = self._resolve()
        if buddy_model is not None:
            kwargs["buddy_model"] = buddy_model
        return cls(**kwargs)


BuddyChatModel = _BuddyChatModelFactory()
