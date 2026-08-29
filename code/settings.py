"""Settings for Buddy Code: API keys, the active model, enabled tools, and
agent options. Persisted as JSON under ``~/.buddy/code_settings.json`` and
applied to the process environment so the Buddy models pick up the keys.

NOTE: keys are stored in plaintext in the user's home dir (fine for a local dev
tool). Use OS keychain integration for production distribution.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

_SETTINGS_PATH = Path(os.getenv("BUDDY_CODE_SETTINGS", Path.home() / ".buddy" / "code_settings.json"))

# Friendly provider -> environment variable name for the API key. The model
# catalog (from buddy.builder.registry) supplies the actual model classes.
PROVIDER_ENV_KEYS: Dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "cohere": "CO_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "xai": "XAI_API_KEY",
    "together": "TOGETHER_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
}

# Sensible defaults for "just works" out of the box.
DEFAULT_MODEL_TYPE = "model.anthropic.claude.Claude"
DEFAULT_MODEL_ID = "claude-sonnet-4-5"


class CodeSettings(BaseModel):
    # Active model: a node-type key from the catalog (e.g. model.anthropic.claude.Claude)
    model_type: str = DEFAULT_MODEL_TYPE
    model_id: str = DEFAULT_MODEL_ID
    temperature: Optional[float] = None

    # provider -> api key
    api_keys: Dict[str, str] = Field(default_factory=dict)

    # Catalog tool-type keys the agent may use, in addition to the built-in
    # workspace tools (file read/write/edit/search/run).
    enabled_tools: List[str] = Field(default_factory=list)

    # Agent behaviour
    enable_shell: bool = True
    reasoning: bool = False
    max_tool_calls: int = 50
    instructions: Optional[str] = None

    def apply_to_env(self) -> None:
        """Export configured API keys into the process environment."""
        for provider, key in self.api_keys.items():
            if not key:
                continue
            env_name = PROVIDER_ENV_KEYS.get(provider, f"{provider.upper()}_API_KEY")
            os.environ[env_name] = key

    def redacted(self) -> "CodeSettings":
        """A copy with API keys masked, for sending to the UI."""
        clone = self.model_copy(deep=True)
        clone.api_keys = {k: ("•" * 8 if v else "") for k, v in self.api_keys.items()}
        return clone


def load_settings() -> CodeSettings:
    if _SETTINGS_PATH.exists():
        try:
            return CodeSettings.model_validate_json(_SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return CodeSettings()


def save_settings(settings: CodeSettings) -> CodeSettings:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
    settings.apply_to_env()
    return settings


def merge_settings_update(current: CodeSettings, update: dict) -> CodeSettings:
    """Apply a partial update from the UI. API keys that come in masked (only
    bullet characters) are preserved rather than overwritten."""
    data = current.model_dump()
    incoming_keys = update.pop("api_keys", None)
    for field, value in update.items():
        if field in data:
            data[field] = value
    merged = CodeSettings.model_validate(data)
    if incoming_keys is not None:
        for provider, key in incoming_keys.items():
            if key and set(key) == {"•"}:
                continue  # masked - keep existing
            merged.api_keys[provider] = key
    return merged


__all__ = [
    "CodeSettings",
    "load_settings",
    "save_settings",
    "merge_settings_update",
    "PROVIDER_ENV_KEYS",
]
