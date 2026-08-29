"""Settings for Buddy Care - the customer-care / BPO capability.

Reuses the same provider/api-key conventions as Buddy Code so a deployment can
share keys. Persisted under ``~/.buddy/care_settings.json``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from buddy.code.settings import PROVIDER_ENV_KEYS

_SETTINGS_PATH = Path(os.getenv("BUDDY_CARE_SETTINGS", Path.home() / ".buddy" / "care_settings.json"))

DEFAULT_MODEL_TYPE = "model.anthropic.claude.Claude"
DEFAULT_MODEL_ID = "claude-sonnet-4-5"

# Keywords that should always route a conversation to a human agent.
DEFAULT_ESCALATION_KEYWORDS = [
    "human", "agent", "representative", "manager", "supervisor",
    "complaint", "lawyer", "legal", "cancel my", "refund", "angry", "furious",
]


class CareSettings(BaseModel):
    # Brand / persona
    company_name: str = "Acme Support"
    bot_name: str = "Aria"
    persona: str = "warm, concise, and genuinely helpful"
    languages: List[str] = Field(default_factory=lambda: ["English"])

    # Model
    model_type: str = DEFAULT_MODEL_TYPE
    model_id: str = DEFAULT_MODEL_ID
    temperature: Optional[float] = 0.3
    api_keys: Dict[str, str] = Field(default_factory=dict)

    # Knowledge grounding (FAQ / policies). Small KBs are injected directly;
    # large KBs should move to RAG (roadmap).
    knowledge_text: str = ""
    knowledge_files: List[str] = Field(default_factory=list)

    # Escalation / handoff
    escalation_keywords: List[str] = Field(default_factory=lambda: list(DEFAULT_ESCALATION_KEYWORDS))
    escalate_on_negative_sentiment: bool = True

    # Channels enabled (web is always on; others are roadmap-pluggable)
    channels: List[str] = Field(default_factory=lambda: ["web"])

    # Extra guidance appended to the support prompt
    instructions: Optional[str] = None

    def apply_to_env(self) -> None:
        for provider, key in self.api_keys.items():
            if not key:
                continue
            env_name = PROVIDER_ENV_KEYS.get(provider, f"{provider.upper()}_API_KEY")
            os.environ[env_name] = key

    def resolved_knowledge(self, max_chars: int = 8000) -> str:
        """Concatenate inline knowledge + readable knowledge files (truncated)."""
        parts: List[str] = []
        if self.knowledge_text.strip():
            parts.append(self.knowledge_text.strip())
        for fp in self.knowledge_files:
            try:
                p = Path(fp)
                if p.exists() and p.suffix.lower() in {".md", ".txt", ".rst", ".csv"}:
                    parts.append(p.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                continue
        text = "\n\n---\n\n".join(parts)
        return text[:max_chars]

    def redacted(self) -> "CareSettings":
        clone = self.model_copy(deep=True)
        clone.api_keys = {k: ("•" * 8 if v else "") for k, v in self.api_keys.items()}
        return clone


def load_settings() -> CareSettings:
    if _SETTINGS_PATH.exists():
        try:
            return CareSettings.model_validate_json(_SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return CareSettings()


def save_settings(settings: CareSettings) -> CareSettings:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
    settings.apply_to_env()
    return settings


def merge_settings_update(current: CareSettings, update: dict) -> CareSettings:
    data = current.model_dump()
    incoming_keys = update.pop("api_keys", None)
    for field, value in update.items():
        if field in data:
            data[field] = value
    merged = CareSettings.model_validate(data)
    if incoming_keys is not None:
        for provider, key in incoming_keys.items():
            if key and set(key) == {"•"}:
                continue
            merged.api_keys[provider] = key
    return merged


__all__ = ["CareSettings", "load_settings", "save_settings", "merge_settings_update", "DEFAULT_ESCALATION_KEYWORDS"]
