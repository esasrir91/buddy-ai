"""Multilingual support utilities for Buddy agents.

Claude demonstrates robust multilingual capabilities across 100+ languages,
with near-English performance in major languages (Spanish 98%, French 97%,
Arabic 97%, Chinese 96%, Japanese 96%, Hindi 96%, etc.).

This module provides:

1. **Language** – a simple dataclass wrapping a language tag and name.
2. **MultilingualConfig** – configure response language at the model or agent
   level.  The language instruction is injected into the system prompt.
3. Helper functions for common language configurations.

Usage::

    from buddy.models.multilingual import MultilingualConfig
    from buddy import Agent

    # Always respond in French regardless of input language
    agent = Agent(
        model=Claude(),
        multilingual=MultilingualConfig(language="fr", enforce=True),
    )

    # Translate between two languages
    agent = Agent(
        model=Claude(),
        multilingual=MultilingualConfig(
            language="ko",
            source_language="de",
            idiomatic=True,
        ),
    )

References
----------
* https://platform.claude.com/docs/en/build-with-claude/multilingual-support
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ISO 639-1 language code → English name map (subset of common languages)
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "pt": "Portuguese",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "nl": "Dutch",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    "pl": "Polish",
    "cs": "Czech",
    "sk": "Slovak",
    "hu": "Hungarian",
    "ro": "Romanian",
    "bg": "Bulgarian",
    "hr": "Croatian",
    "sr": "Serbian",
    "uk": "Ukrainian",
    "ru": "Russian",
    "tr": "Turkish",
    "ar": "Arabic",
    "he": "Hebrew",
    "fa": "Persian",
    "hi": "Hindi",
    "bn": "Bengali",
    "ur": "Urdu",
    "te": "Telugu",
    "ta": "Tamil",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "zh": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ja": "Japanese",
    "ko": "Korean",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
    "sw": "Swahili",
    "yo": "Yoruba",
    "am": "Amharic",
}


@dataclass
class MultilingualConfig:
    """Configure multilingual behavior for a model or agent.

    Attributes:
        language: Target response language as a BCP-47 / ISO 639-1 code
            (e.g. ``"fr"``, ``"zh"``, ``"ar"``).  If ``None`` the model
            infers the language from the conversation.
        source_language: When set, instruct the model to translate *from*
            this language *to* ``language``.
        idiomatic: When ``True``, ask the model to respond "as a native
            speaker" for more natural phrasing.
        enforce: When ``True``, use stronger language ("Always respond in …,
            regardless of the language the user writes in").
        include_language_name: Include the full language name in the prompt
            alongside the code for clarity.
    """

    language: Optional[str] = None
    source_language: Optional[str] = None
    idiomatic: bool = False
    enforce: bool = False
    include_language_name: bool = True

    def __post_init__(self) -> None:
        if self.language:
            self.language = self.language.lower()
        if self.source_language:
            self.source_language = self.source_language.lower()

    def to_system_prompt_fragment(self) -> str:
        """Return the system-prompt instruction for language control.

        Returns an empty string when no language is configured.
        """
        if not self.language:
            return ""

        lang_str = self._lang_str(self.language)
        source_str = self._lang_str(self.source_language) if self.source_language else None

        if source_str:
            instruction = (
                f"Translate the user's message from {source_str} to {lang_str}. "
                "Respond with only the translation."
            )
            return instruction

        if self.enforce:
            instruction = f"Always respond in {lang_str}, regardless of the language the user writes in."
        else:
            instruction = f"Respond in {lang_str}."

        if self.idiomatic:
            instruction += f" Use idiomatic {lang_str} as if you were a native speaker."

        return instruction

    def _lang_str(self, code: str) -> str:
        if self.include_language_name:
            name = LANGUAGE_NAMES.get(code)
            if name:
                return name
        return code.upper()


# ── Convenience constructors ───────────────────────────────────────────────────

def always_respond_in(language: str, idiomatic: bool = True) -> MultilingualConfig:
    """Always respond in *language*, regardless of the user's input language."""
    return MultilingualConfig(language=language, enforce=True, idiomatic=idiomatic)


def translate(source: str, target: str) -> MultilingualConfig:
    """Translate from *source* language to *target* language."""
    return MultilingualConfig(language=target, source_language=source)
