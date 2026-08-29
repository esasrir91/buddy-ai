"""Agent Skills system for Buddy — provider-agnostic.

A Skill is a reusable, filesystem-based capability that gives an agent
domain-specific expertise: workflows, context, and best practices that turn a
general-purpose agent into a specialist.

Architecture
------------
Each Skill lives in a directory containing:

* ``SKILL.md`` — primary instruction file with YAML front matter.
  The front matter ``name`` and ``description`` fields are loaded at startup
  and injected into the system prompt as lightweight metadata.  The full
  body is loaded only when the Skill is triggered.
* Optional resource files (scripts, templates, data) loaded on demand.

Three-level progressive disclosure
-----------------------------------
1. **Metadata** (``name`` + ``description`` from front matter) — always in
   the system prompt; negligible token cost.
2. **Instructions** (full ``SKILL.md`` body) — loaded when the Skill is
   triggered by the model.
3. **Resources** (files referenced in ``SKILL.md``) — loaded on demand.

Anthropic Skills API integration
---------------------------------
When the Anthropic ``anthropic`` package is present and an API key is set,
:func:`upload_skill` / :func:`upload_skill_async` upload the skill directory
to the Anthropic Skills API (``/v1/skills``).  The returned ``skill_id`` can
then be referenced in the ``container`` parameter of Messages API requests.

Generic provider support
------------------------
For all other LLMs, Skills are injected as system-prompt additions:
:func:`build_system_prompt_from_skills` generates a compact header listing
all active skills and their descriptions, plus the full instruction body for
any that have been triggered.

References
----------
* https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
* https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
* https://platform.claude.com/docs/en/agents-and-tools/agent-skills/enterprise
* https://platform.claude.com/docs/en/build-with-claude/skills-guide
"""

from __future__ import annotations

import os
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Front-matter parsing
# ---------------------------------------------------------------------------

_FRONT_MATTER_RE = re.compile(
    r"^---\s*\n(?P<fm>.*?)\n---\s*\n(?P<body>.*)",
    re.DOTALL,
)


def _parse_front_matter(text: str) -> Tuple[Dict[str, str], str]:
    """Parse YAML-like front matter from a SKILL.md string.

    Only handles simple ``key: value`` pairs (no nested YAML); that is all
    Anthropic's Skill spec requires.  Returns ``(front_matter_dict, body)``.
    """
    m = _FRONT_MATTER_RE.match(text.lstrip())
    if not m:
        return {}, text

    fm_text = m.group("fm")
    body = m.group("body")

    fm: Dict[str, str] = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()

    return fm, body


# ---------------------------------------------------------------------------
# Skill dataclass
# ---------------------------------------------------------------------------


@dataclass
class Skill:
    """A single Agent Skill loaded from a directory or defined in code.

    Attributes:
        name: Short kebab-case identifier (e.g. ``"pdf-processing"``).
        description: One-sentence trigger description for the system prompt.
            Must say *what* the Skill does **and** *when* to use it.
        instructions: Full procedural body (loaded from ``SKILL.md``).
        directory: Filesystem path to the Skill directory (optional).
        skill_id: Anthropic Skills API ``skill_id`` (set after upload).
        version: Skill version string or Anthropic version ID.
        resources: Map of filename → content for bundled resource files.
        tags: Free-form tags for filtering/grouping.
        source: ``"anthropic"`` for pre-built, ``"custom"`` for uploaded, or
            ``"local"`` for locally defined (not yet uploaded).
        enabled: When ``False``, the Skill is loaded but not injected.
    """

    name: str
    description: str
    instructions: str = ""
    directory: Optional[str] = None
    skill_id: Optional[str] = None
    version: Optional[str] = None
    resources: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    source: str = "local"  # "anthropic" | "custom" | "local"
    enabled: bool = True

    # ── Metadata helpers ─────────────────────────────────────────────────────

    @property
    def metadata_line(self) -> str:
        """Single-line metadata entry for the system prompt."""
        return f"- **{self.name}**: {self.description}"

    def as_system_block(self, include_instructions: bool = False) -> str:
        """Format the Skill as a system-prompt block.

        Args:
            include_instructions: Include the full instruction body.

        Returns:
            Markdown-formatted string.
        """
        lines = [f"### Skill: {self.name}", f"{self.description}"]
        if include_instructions and self.instructions:
            lines.append("")
            lines.append(self.instructions.strip())
        return "\n".join(lines)

    def as_anthropic_container_entry(self, version: Optional[str] = None) -> Dict[str, Any]:
        """Return the ``container.skills`` entry for Anthropic Messages API.

        Args:
            version: Override the Skill's version string.

        Returns:
            Dict with ``type``, ``skill_id``, and optionally ``version``.
        """
        entry: Dict[str, Any] = {
            "type": self.source if self.source in ("anthropic", "custom") else "custom",
            "skill_id": self.skill_id or self.name,
        }
        ver = version or self.version
        if ver:
            entry["version"] = ver
        return entry

    # ── Loading helpers ──────────────────────────────────────────────────────

    @classmethod
    def from_directory(cls, directory: Union[str, Path]) -> "Skill":
        """Load a Skill from a filesystem directory.

        Expects a ``SKILL.md`` file in the directory.  Optional resource files
        are loaded from the same directory.

        Args:
            directory: Path to the Skill directory.

        Returns:
            :class:`Skill` with metadata and instructions populated.
        """
        d = Path(directory)
        skill_md = d / "SKILL.md"

        if not skill_md.exists():
            raise FileNotFoundError(
                f"SKILL.md not found in {d}. "
                "Each Skill directory must contain a SKILL.md file."
            )

        text = skill_md.read_text(encoding="utf-8")
        fm, body = _parse_front_matter(text)

        name = fm.get("name", d.name)
        description = fm.get("description", "")

        # Load resource files (everything that isn't SKILL.md)
        resources: Dict[str, str] = {}
        for f in d.iterdir():
            if f.name == "SKILL.md" or f.name.startswith("."):
                continue
            try:
                resources[f.name] = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

        return cls(
            name=name,
            description=description,
            instructions=body.strip(),
            directory=str(d),
            resources=resources,
            source="local",
        )

    @classmethod
    def from_markdown(
        cls,
        text: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> "Skill":
        """Create a Skill directly from a SKILL.md-format string.

        Args:
            text: Full SKILL.md content (with or without front matter).
            name: Override the ``name`` from front matter.
            description: Override the ``description`` from front matter.

        Returns:
            :class:`Skill` instance.
        """
        fm, body = _parse_front_matter(text)
        return cls(
            name=name or fm.get("name", "unnamed-skill"),
            description=description or fm.get("description", ""),
            instructions=body.strip(),
            source="local",
        )


# ---------------------------------------------------------------------------
# Skill registry
# ---------------------------------------------------------------------------


@dataclass
class SkillRegistry:
    """A collection of Skills available to an agent.

    Skills are looked up by name.  The registry provides helpers for
    injecting skill metadata into system prompts and for building the
    ``container`` parameter for Anthropic API calls.

    Attributes:
        skills: Ordered list of registered Skills.
        max_skills_per_request: Anthropic API limit (20).
        auto_trigger: When ``True``, include all enabled skills'
            instructions in the system prompt.  When ``False``, only
            metadata is included (the Skill is triggered at inference time
            by the model).
    """

    skills: List[Skill] = field(default_factory=list)
    max_skills_per_request: int = 20
    auto_trigger: bool = False

    # ── Mutation helpers ─────────────────────────────────────────────────────

    def register(self, skill: Skill) -> None:
        """Add *skill* to the registry."""
        # Replace existing skill with the same name
        self.skills = [s for s in self.skills if s.name != skill.name]
        self.skills.append(skill)

    def register_directory(self, directory: Union[str, Path]) -> Skill:
        """Load and register a Skill from a filesystem directory."""
        skill = Skill.from_directory(directory)
        self.register(skill)
        return skill

    def register_all_in(self, parent_directory: Union[str, Path]) -> List[Skill]:
        """Scan *parent_directory* for Skill directories and register each one.

        A directory is treated as a Skill directory when it contains a
        ``SKILL.md`` file.
        """
        registered: List[Skill] = []
        for entry in Path(parent_directory).iterdir():
            if entry.is_dir() and (entry / "SKILL.md").exists():
                try:
                    skill = self.register_directory(entry)
                    registered.append(skill)
                except Exception:
                    pass
        return registered

    def get(self, name: str) -> Optional[Skill]:
        """Return the Skill with *name*, or ``None``."""
        for s in self.skills:
            if s.name == name:
                return s
        return None

    def enable(self, name: str) -> None:
        """Enable the Skill named *name*."""
        s = self.get(name)
        if s:
            s.enabled = True

    def disable(self, name: str) -> None:
        """Disable the Skill named *name*."""
        s = self.get(name)
        if s:
            s.enabled = False

    # ── Active skills ────────────────────────────────────────────────────────

    @property
    def active(self) -> List[Skill]:
        """Return enabled Skills, limited to ``max_skills_per_request``."""
        return [s for s in self.skills if s.enabled][: self.max_skills_per_request]

    # ── System-prompt injection ───────────────────────────────────────────────

    def build_metadata_header(self) -> str:
        """Return a compact system-prompt header listing all active Skills.

        Only name + description are included.  The full instructions are
        loaded by the model on demand (or injected via
        :meth:`build_full_system_block`).
        """
        if not self.active:
            return ""
        lines = [
            "## Available Agent Skills",
            "The following Skills are available. Use a Skill when a user request "
            "matches its description.",
            "",
        ]
        for s in self.active:
            lines.append(s.metadata_line)
        return "\n".join(lines)

    def build_full_system_block(self, triggered: Optional[List[str]] = None) -> str:
        """Return a system block with full instructions for triggered Skills.

        Args:
            triggered: List of Skill names to include instructions for.
                When ``None``, includes all active Skills (if ``auto_trigger``
                is ``True``) or just the metadata header.

        Returns:
            Markdown string to append to the system prompt.
        """
        parts: List[str] = []
        header = self.build_metadata_header()
        if header:
            parts.append(header)

        include_instructions = triggered or (self.active if self.auto_trigger else [])
        trigger_names: set = {s.name for s in include_instructions} if isinstance(include_instructions, list) else set(triggered or [])

        for skill in self.active:
            if skill.name in trigger_names and skill.instructions:
                parts.append("")
                parts.append(f"## Skill instructions: {skill.name}")
                parts.append(skill.instructions)

        return "\n".join(parts)

    # ── Anthropic API integration ─────────────────────────────────────────────

    def anthropic_container(
        self,
        skill_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Return the ``container`` parameter for the Anthropic Messages API.

        Args:
            skill_names: Restrict to these Skill names.  ``None`` includes all
                active Skills that have a ``skill_id``.

        Returns:
            ``{"skills": [...]}`` dict or ``{}`` when no uploadable skills.
        """
        candidates = self.active
        if skill_names is not None:
            candidates = [s for s in candidates if s.name in skill_names]

        uploadable = [s for s in candidates if s.skill_id]
        if not uploadable:
            return {}

        return {
            "skills": [s.as_anthropic_container_entry() for s in uploadable]
        }

    def anthropic_required_tools(self) -> List[Dict[str, Any]]:
        """Return the code execution tool definition required for Anthropic Skills."""
        return [{"type": "code_execution_20250825", "name": "code_execution"}]


# ---------------------------------------------------------------------------
# Anthropic Skills API — upload / manage
# ---------------------------------------------------------------------------


def upload_skill(
    skill_or_directory: Union[Skill, str, Path],
    api_key: Optional[str] = None,
    version: Optional[str] = None,
) -> Optional[str]:
    """Upload a Skill to the Anthropic Skills API.

    On success, sets ``skill.skill_id`` and ``skill.version`` and returns the
    ``skill_id``.  Returns ``None`` when the upload fails or the package is
    unavailable.

    Args:
        skill_or_directory: A :class:`Skill` instance or a path to a Skill
            directory.
        api_key: Anthropic API key (falls back to ``ANTHROPIC_API_KEY``).
        version: Version string to pin (optional).

    Returns:
        The Anthropic ``skill_id`` string, or ``None``.
    """
    if isinstance(skill_or_directory, (str, Path)):
        skill = Skill.from_directory(skill_or_directory)
    else:
        skill = skill_or_directory

    try:
        from anthropic import Anthropic
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            return None

        client = Anthropic(api_key=key)

        # Build SKILL.md content from the skill object
        skill_md = f"---\nname: {skill.name}\ndescription: {skill.description}\n---\n\n{skill.instructions}"

        response = client.skills.create(  # type: ignore[attr-defined]
            name=skill.name,
            description=skill.description,
            skill_markdown=skill_md,
        )

        skill_id = str(getattr(response, "id", "") or getattr(response, "skill_id", ""))
        if skill_id:
            skill.skill_id = skill_id
            skill.version = version or getattr(response, "version", None)
            skill.source = "custom"

        return skill_id or None

    except Exception:
        return None


async def upload_skill_async(
    skill_or_directory: Union[Skill, str, Path],
    api_key: Optional[str] = None,
    version: Optional[str] = None,
) -> Optional[str]:
    """Async variant of :func:`upload_skill`."""
    if isinstance(skill_or_directory, (str, Path)):
        skill = Skill.from_directory(skill_or_directory)
    else:
        skill = skill_or_directory

    try:
        from anthropic import AsyncAnthropic
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            return None

        client = AsyncAnthropic(api_key=key)

        skill_md = f"---\nname: {skill.name}\ndescription: {skill.description}\n---\n\n{skill.instructions}"

        response = await client.skills.create(  # type: ignore[attr-defined]
            name=skill.name,
            description=skill.description,
            skill_markdown=skill_md,
        )

        skill_id = str(getattr(response, "id", "") or getattr(response, "skill_id", ""))
        if skill_id:
            skill.skill_id = skill_id
            skill.version = version or getattr(response, "version", None)
            skill.source = "custom"

        return skill_id or None

    except Exception:
        return None


def list_remote_skills(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all Skills in the Anthropic workspace.

    Returns a list of dicts; returns ``[]`` on failure.
    """
    try:
        from anthropic import Anthropic
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            return []
        client = Anthropic(api_key=key)
        page = client.skills.list()  # type: ignore[attr-defined]
        items = page.data if hasattr(page, "data") else list(page)
        return [
            {
                "skill_id": getattr(s, "id", None) or getattr(s, "skill_id", None),
                "name": getattr(s, "name", ""),
                "description": getattr(s, "description", ""),
                "source": getattr(s, "source", "custom"),
                "version": getattr(s, "version", None),
            }
            for s in items
        ]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Pre-built Anthropic Skills
# ---------------------------------------------------------------------------


#: Pre-built Anthropic Skills available to all users.
ANTHROPIC_SKILLS: Dict[str, "Skill"] = {
    "pptx": Skill(
        name="pptx",
        description=(
            "Create and edit PowerPoint presentations. "
            "Use when the user wants to create a presentation, slide deck, "
            "or .pptx file."
        ),
        skill_id="pptx",
        source="anthropic",
    ),
    "xlsx": Skill(
        name="xlsx",
        description=(
            "Create and edit Excel spreadsheets. "
            "Use when the user wants to create a spreadsheet, chart, or .xlsx file."
        ),
        skill_id="xlsx",
        source="anthropic",
    ),
    "docx": Skill(
        name="docx",
        description=(
            "Create and edit Word documents. "
            "Use when the user wants to create a document, report, or .docx file."
        ),
        skill_id="docx",
        source="anthropic",
    ),
    "pdf": Skill(
        name="pdf",
        description=(
            "Create PDF files from text or convert other formats to PDF. "
            "Use when the user wants to create a PDF or convert a document to PDF."
        ),
        skill_id="pdf",
        source="anthropic",
    ),
}


def get_anthropic_skill(name: str, version: str = "latest") -> Optional[Skill]:
    """Return a pre-built Anthropic Skill by name."""
    skill = ANTHROPIC_SKILLS.get(name)
    if skill is None:
        return None
    import copy
    s = copy.copy(skill)
    s.version = version
    return s


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def skill(
    name: str,
    description: str,
    instructions: str = "",
    tags: Optional[List[str]] = None,
) -> Skill:
    """Convenience constructor for a locally-defined Skill."""
    return Skill(
        name=name,
        description=description,
        instructions=instructions,
        tags=tags or [],
        source="local",
    )


def skill_from_directory(directory: Union[str, Path]) -> Skill:
    """Load and return a Skill from a SKILL.md directory."""
    return Skill.from_directory(directory)


# ---------------------------------------------------------------------------
# Type alias for Union support
# ---------------------------------------------------------------------------
from typing import Union  # noqa: E402  (moved here to avoid circular import concerns)
