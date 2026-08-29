"""Shared plumbing for Varam AI vertical packs.

Provides a common settings base (model + API keys + firm identity + knowledge),
a model builder, the regulated-profession disclaimers, and a generic agent
assembler so each pack only has to declare its prompt and its domain tools.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from buddy.code.agent import _accepts, _resolve_class
from buddy.code.settings import PROVIDER_ENV_KEYS

DEFAULT_MODEL_TYPE = "model.anthropic.claude.Claude"
DEFAULT_MODEL_ID = "claude-sonnet-4-5"

# Mandatory disclaimers - regulated professions. The agent must never present
# output as a certified/final opinion; a qualified human signs off.
DISCLAIMERS: Dict[str, str] = {
    "ca": (
        "This output is an AI-assisted working draft, not professional advice or "
        "an audit opinion. It must be reviewed, verified against source records, "
        "and signed by a qualified Chartered Accountant before any filing or "
        "reliance. Tax/GST positions depend on current law and facts."
    ),
    "valuation": (
        "This is an AI-assisted draft analysis, not a registered valuer's report "
        "or investment advice. A Registered Valuer (IBBI) / qualified professional "
        "must independently verify inputs, assumptions and methodology and issue "
        "the final valuation under the applicable Valuation Standards."
    ),
    "civil": (
        "This output is an AI-assisted estimate/check for planning support only. "
        "It is NOT a stamped structural design or certified BOQ. A licensed "
        "civil/structural engineer must verify all quantities, loads, codes and "
        "site conditions and certify the final design and estimate."
    ),
}

# Indian standards / authoritative sources per pack (pointers, not redistributed text).
SEED_SOURCES: Dict[str, List[str]] = {
    "ca": [
        "Income-tax Act, 1961 (incometaxindia.gov.in)",
        "CGST/SGST/IGST Acts & GST Rules (cbic-gst.gov.in)",
        "Companies Act, 2013 & Schedule III (mca.gov.in)",
        "ICAI Accounting Standards (AS), Ind AS, and Standards on Auditing (SA)",
    ],
    "valuation": [
        "ICAI Valuation Standards (ICAI VS 2018)",
        "IBBI (Registered Valuers and Valuation) Rules, 2017",
        "International Valuation Standards (IVS)",
        "Companies (Registered Valuers and Valuation) Rules",
    ],
    "civil": [
        "IS 456:2000 (Plain & Reinforced Concrete)",
        "IS 800:2007 (General Construction in Steel)",
        "IS 875 (Loads), IS 1893 (Seismic)",
        "CPWD / State PWD Schedule of Rates (SOR)",
    ],
}


class VerticalSettings(BaseModel):
    """Common configuration for a vertical copilot."""

    pack: str = "ca"  # ca | valuation | civil
    firm_name: str = "Your Firm"
    professional_name: str = ""  # e.g. the signing CA / Registered Valuer / Engineer
    membership_no: str = ""      # ICAI membership / IBBI reg. no / PEng licence

    # Model
    model_type: str = DEFAULT_MODEL_TYPE
    model_id: str = DEFAULT_MODEL_ID
    temperature: Optional[float] = 0.2
    api_keys: Dict[str, str] = Field(default_factory=dict)

    # Where reports/spreadsheets are written
    workspace: str = ""

    # Optional grounding text + reference files
    knowledge_text: str = ""
    knowledge_files: List[str] = Field(default_factory=list)

    # Extra firm-specific guidance appended to the system prompt
    instructions: Optional[str] = None

    def apply_to_env(self) -> None:
        for provider, key in self.api_keys.items():
            if not key:
                continue
            env_name = PROVIDER_ENV_KEYS.get(provider, f"{provider.upper()}_API_KEY")
            os.environ[env_name] = key

    def resolved_knowledge(self, max_chars: int = 8000) -> str:
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
        return ("\n\n---\n\n".join(parts))[:max_chars]

    def workspace_dir(self) -> str:
        return self.workspace or str(Path.cwd())

    def redacted(self) -> "VerticalSettings":
        clone = self.model_copy(deep=True)
        clone.api_keys = {k: ("\u2022" * 8 if v else "") for k, v in self.api_keys.items()}
        return clone


def bundled_knowledge(pack: str, max_chars: int = 6000) -> str:
    """Load the pack's bundled reference notes (buddy/verticals/<pack>/knowledge/*.md)."""
    kb_dir = Path(__file__).parent / pack / "knowledge"
    if not kb_dir.is_dir():
        return ""
    parts: List[str] = []
    for md in sorted(kb_dir.glob("*.md")):
        try:
            parts.append(md.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
    return ("\n\n".join(parts))[:max_chars]


def build_model(settings: VerticalSettings):
    cls = _resolve_class(settings.model_type)
    kwargs: Dict[str, Any] = {"id": settings.model_id}
    # Skip temperature for models that reject it (Claude 4.7+/5, OpenAI reasoning).
    wants_temp = settings.temperature is not None and _accepts(cls, "temperature")
    if wants_temp:
        supports = getattr(cls, "supports_temperature", None)
        if supports is None or supports(settings.model_id):
            kwargs["temperature"] = settings.temperature
    provider = settings.model_type.split(".")[1] if "." in settings.model_type else ""
    api_key = settings.api_keys.get(provider)
    if api_key and _accepts(cls, "api_key"):
        kwargs["api_key"] = api_key
    return cls(**kwargs)


def build_vertical_agent(settings: VerticalSettings, name: str, system_prompt: str, tools: List[Any]):
    """Assemble a vertical copilot Agent with the pack disclaimer baked in."""
    from buddy.agent import Agent

    settings.apply_to_env()
    disclaimer = DISCLAIMERS.get(settings.pack, "")
    sources = SEED_SOURCES.get(settings.pack, [])

    instructions: List[str] = [system_prompt.format(firm_name=settings.firm_name)]
    instructions.append(
        "ACCURACY: Never compute figures in your head. Use the deterministic tools "
        "(finance/excel/calculator/python) for every calculation and show the working. "
        "Cite the source record or standard for each material number."
    )
    if sources:
        instructions.append("AUTHORITATIVE SOURCES (verify against the latest official text):\n- " + "\n- ".join(sources))
    ref = bundled_knowledge(settings.pack)
    if ref:
        instructions.append("DOMAIN REFERENCE (indicative cheat-sheet; confirm current rates/clauses):\n" + ref)
    if disclaimer:
        instructions.append(
            "COMPLIANCE: You are a co-pilot, not the certifying professional. Add this "
            f"disclaimer to every deliverable and recommend human sign-off:\n{disclaimer}"
        )
    kb = settings.resolved_knowledge()
    if kb:
        instructions.append("FIRM KNOWLEDGE (reference):\n" + kb)
    if settings.instructions:
        instructions.append(settings.instructions)

    return Agent(
        name=name,
        model=build_model(settings),
        tools=tools,
        instructions=instructions,
        markdown=True,
        add_history_to_messages=True,
        num_history_runs=8,
    )


__all__ = [
    "VerticalSettings",
    "build_model",
    "build_vertical_agent",
    "DISCLAIMERS",
    "SEED_SOURCES",
    "DEFAULT_MODEL_TYPE",
    "DEFAULT_MODEL_ID",
]
