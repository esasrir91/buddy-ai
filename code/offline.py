"""Offline / local LLM support via Ollama - a free, lightweight way to run models
fully offline for basic use. Buddy already ships an Ollama model wrapper; this
module detects the local Ollama runtime and lists installed models.
"""

from __future__ import annotations

from typing import Any, Dict, List

# The Buddy model class used for offline inference.
OLLAMA_MODEL_TYPE = "model.ollama.chat.Ollama"
# A small, capable default that runs on modest hardware.
DEFAULT_OFFLINE_MODEL = "llama3.2"
SUGGESTED_MODELS = ["llama3.2", "llama3.2:1b", "qwen2.5:3b", "phi3.5", "gemma2:2b", "mistral"]


def offline_status() -> Dict[str, Any]:
    """Report whether Ollama is usable and which local models are installed."""
    status: Dict[str, Any] = {
        "available": False,
        "package_installed": False,
        "server_running": False,
        "models": [],
        "model_type": OLLAMA_MODEL_TYPE,
        "default_model": DEFAULT_OFFLINE_MODEL,
        "suggested": SUGGESTED_MODELS,
        "message": "",
    }
    try:
        import ollama  # type: ignore
    except Exception:
        status["message"] = "Ollama not installed. Run `pip install ollama` and install Ollama from ollama.com."
        return status
    status["package_installed"] = True
    try:
        listed = ollama.list()
        models: List[str] = []
        for m in listed.get("models", []):
            name = m.get("model") or m.get("name")
            if name:
                models.append(name)
        status["server_running"] = True
        status["available"] = True
        status["models"] = models
        status["message"] = (
            "Ollama is ready." if models else "Ollama is running but no models are installed. "
            f"Run e.g. `ollama pull {DEFAULT_OFFLINE_MODEL}`."
        )
    except Exception as exc:  # noqa: BLE001
        status["message"] = f"Ollama installed but the server is not reachable ({exc}). Start it with `ollama serve`."
    return status


__all__ = ["offline_status", "OLLAMA_MODEL_TYPE", "DEFAULT_OFFLINE_MODEL", "SUGGESTED_MODELS"]
