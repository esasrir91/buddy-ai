"""
PULSE Knowledge Transfer (KT) Engine — how PULSE learns from humans and documents.

KTSourceType    : What kind of source a KT session is based on.
KTPhase         : The current phase of a live KT dialogue.
KTTurn          : One PULSE response turn in a live KT session.
KTSessionState  : Mutable state of a running KT session.
KTSummary       : The final output of a completed KT session.
KTSession       : Manages an active KT session (async OR live human mode).
KTManager       : Factory and registry for KT sessions.
"""
from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from buddy.pulse.employee import PulseEmployee


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class KTSourceType(str, Enum):
    # Async / document modes
    DOCUMENT = "document"
    URL = "url"
    AUDIO_TRANSCRIPT = "audio_transcript"
    VIDEO_TRANSCRIPT = "video_transcript"
    WIKI_PAGE = "wiki_page"
    MEETING_RECORDING = "meeting_recording"
    CODEBASE = "codebase"
    # Live / human modes  (prefix HUMAN_ activates interactive dialogue loop)
    HUMAN_CHAT = "human_chat"
    HUMAN_VOICE_CALL = "human_voice_call"
    HUMAN_SLACK_THREAD = "human_slack_thread"
    HUMAN_VIDEO_CALL = "human_video_call"

    @property
    def is_human_mode(self) -> bool:
        return self.value.startswith("human_")

    @property
    def is_async_mode(self) -> bool:
        return not self.is_human_mode


class KTPhase(str, Enum):
    LISTENING = "listening"
    QUESTIONING = "questioning"
    SUMMARIZING = "summarizing"
    CONFIRMING = "confirming"
    COMPLETED = "completed"


# ---------------------------------------------------------------------------
# KTTurn — one PULSE response in a live dialogue
# ---------------------------------------------------------------------------

class KTTurn(BaseModel):
    """One PULSE response turn during a live KT dialogue."""

    turn_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    phase: KTPhase
    pulse_message: str = Field(..., description="What PULSE says/asks next")
    questions: List[str] = Field(default_factory=list, description="Populated when phase == QUESTIONING")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Current understanding confidence")
    mental_model_draft: str = Field(default="", description="PULSE's working understanding so far")
    ready_to_commit: bool = Field(default=False, description="True when PULSE believes it has understood")


# ---------------------------------------------------------------------------
# KTSummary — final output of a completed KT session
# ---------------------------------------------------------------------------

class KTSummary(BaseModel):
    """The final structured output of a completed KT session."""

    session_id: str
    session_name: str
    knowledge_giver: str
    source_type: KTSourceType
    mode: Literal["async", "live"]

    key_concepts: List[str] = Field(default_factory=list)
    mental_model: str = Field(default="", description="PULSE's understanding in their own words")
    open_questions: List[str] = Field(default_factory=list)
    connections_to_existing_knowledge: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    rounds_of_dialogue: int = Field(default=0, description="0 for async mode")
    domain: str = ""
    tags: List[str] = Field(default_factory=list)
    completed_at: datetime = Field(default_factory=datetime.utcnow)

    def format_summary(self) -> str:
        lines = [
            f"## KT Summary — {self.session_name}",
            f"Knowledge giver: {self.knowledge_giver}",
            f"Source: {self.source_type.value} ({self.mode} mode)",
            f"Confidence: {self.confidence_score:.0%}",
            "",
            f"**My Understanding:**\n{self.mental_model}",
        ]
        if self.key_concepts:
            lines.append(f"\n**Key Concepts:** {', '.join(self.key_concepts)}")
        if self.open_questions:
            lines.append("\n**Open Questions:**")
            for q in self.open_questions:
                lines.append(f"  - {q}")
        if self.connections_to_existing_knowledge:
            lines.append("\n**Connects to what I already know:**")
            for c in self.connections_to_existing_knowledge:
                lines.append(f"  - {c}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# KTSessionState — mutable state of a running KT session
# ---------------------------------------------------------------------------

class KTSessionState(BaseModel):
    """Mutable state of an in-progress KT session."""

    session_id: str
    session_name: str
    source_type: KTSourceType
    mode: Literal["async", "live"]
    phase: KTPhase = KTPhase.LISTENING
    rounds_completed: int = 0
    confidence_score: float = 0.0
    pending_questions: List[str] = Field(default_factory=list)
    mental_model_draft: str = ""
    key_concepts: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    dialogue_history: List[Dict[str, str]] = Field(default_factory=list)
    committed: bool = False
    started_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# KTSession — the active session object
# ---------------------------------------------------------------------------

class KTSession:
    """
    Manages an active KT session for a PULSE employee.

    Two modes:
      async  — PULSE ingests a document/URL/transcript and auto-processes it.
      live   — A human explains something; PULSE drives a Socratic dialogue
               until its confidence score reaches the threshold.

    Usage (async):
        session = KTSession(employee, "Payments Architecture", KTSourceType.DOCUMENT, ...)
        session.ingest("path/to/doc.pdf")
        summary = session.generate_summary()
        session.commit()

    Usage (live/human):
        session = pulse.start_live_kt(...)
        turn = session.human_explains("Our auth service uses JWTs with 1-hour expiry...")
        print(turn.pulse_message)       # PULSE's questions
        turn = session.human_answers({...})
        session.human_corrects("One thing I missed...")
        summary = session.generate_summary()
        session.commit()
    """

    CONFIDENCE_THRESHOLD: float = 0.82
    MAX_ROUNDS: int = 12

    def __init__(
        self,
        employee: "PulseEmployee",
        session_name: str,
        source_type: KTSourceType,
        knowledge_giver: str,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        max_rounds: int = MAX_ROUNDS,
    ) -> None:
        self.employee = employee
        self.knowledge_giver = knowledge_giver
        self.confidence_threshold = confidence_threshold
        self.max_rounds = max_rounds
        self.state = KTSessionState(
            session_id=str(uuid4()),
            session_name=session_name,
            source_type=source_type,
            mode="live" if source_type.is_human_mode else "async",
        )

    @property
    def session_id(self) -> str:
        return self.state.session_id

    @property
    def is_live(self) -> bool:
        return self.state.mode == "live"

    # ----------------------------------------------------------------- Async
    def ingest(self, source: Union[str, Path, bytes]) -> "KTSession":
        """
        Phase 1–3 for async mode: read the source, build mental model,
        and prepare clarifying questions. Returns self for chaining.
        """
        source_text = self._read_source(source)
        prompt = self._build_ingest_prompt(source_text)
        response = self._call_model(prompt)
        data = self._parse_json(response)
        self.state.mental_model_draft = data.get("mental_model", "")
        self.state.key_concepts = data.get("key_concepts", [])
        self.state.pending_questions = data.get("clarifying_questions", [])
        self.state.confidence_score = float(data.get("confidence_score", 0.6))
        self.state.phase = KTPhase.QUESTIONING if self.state.pending_questions else KTPhase.SUMMARIZING
        return self

    def _read_source(self, source: Union[str, Path, bytes]) -> str:
        if isinstance(source, bytes):
            return source.decode("utf-8", errors="replace")
        source_str = str(source) if not isinstance(source, Path) else str(source)

        # Crawl URL and all internal links
        if source_str.startswith(("http://", "https://")):
            return self._crawl_url(source_str)

        path = Path(source_str)
        if path.exists():
            suffix = path.suffix.lower()
            if suffix == ".pdf":
                return self._read_pdf(path)
            return path.read_text(encoding="utf-8", errors="replace")
        return source_str

    @staticmethod
    def _read_pdf(path: Path) -> str:
        """Extract plain text from a PDF file using pypdf or pdfplumber."""
        text_parts: List[str] = []

        # Try pypdf first (pip install pypdf)
        try:
            import pypdf  # type: ignore
            reader = pypdf.PdfReader(str(path))
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
            if text_parts:
                return "\n\n".join(text_parts)
        except ImportError:
            pass
        except Exception:
            pass

        # Try pdfplumber (pip install pdfplumber)
        try:
            import pdfplumber  # type: ignore
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text_parts.append(t)
            if text_parts:
                return "\n\n".join(text_parts)
        except ImportError:
            pass
        except Exception:
            pass

        # Last resort: raw bytes, decode loosely
        return path.read_bytes().decode("utf-8", errors="replace")

    @staticmethod
    def _crawl_url(
        start_url: str,
        max_pages: int = 20,
        max_depth: int = 3,
        per_page_chars: int = 4000,
        total_chars: int = 30000,
    ) -> str:
        """
        BFS-crawl a URL and its same-domain internal links.

        - Stays on the same domain as the start URL
        - Visits at most `max_pages` pages, up to `max_depth` link-hops away
        - Strips HTML tags, scripts, and styles from each page
        - Returns all page text joined together (capped at `total_chars`)
        """
        import re
        import httpx
        from collections import deque
        from urllib.parse import urljoin, urlparse, urldefrag

        HEADERS = {"User-Agent": "BuddyAI-PULSE/2.1 (KT crawler; +https://github.com/esasrir91/buddy-ai)"}

        def _clean_html(html: str) -> str:
            text = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.S | re.I)
            text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.S | re.I)
            text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text.strip()

        def _extract_links(html: str, base_url: str, allowed_netloc: str) -> List[str]:
            links = []
            for href in re.findall(r'href=["\']([^"\'#?][^"\']*)["\']', html, re.I):
                abs_url, _ = urldefrag(urljoin(base_url, href))
                if urlparse(abs_url).netloc == allowed_netloc and abs_url.startswith("http"):
                    links.append(abs_url)
            return links

        allowed_netloc = urlparse(start_url).netloc
        visited: set = set()
        queue: deque = deque([(start_url, 0)])
        pages: List[str] = []
        total = 0

        with httpx.Client(timeout=15, follow_redirects=True, headers=HEADERS) as client:
            while queue and len(visited) < max_pages:
                url, depth = queue.popleft()
                clean_url, _ = urldefrag(url)
                if clean_url in visited:
                    continue
                visited.add(clean_url)

                try:
                    resp = client.get(clean_url)
                    resp.raise_for_status()
                    ctype = resp.headers.get("content-type", "")
                    if "html" not in ctype and "text" not in ctype:
                        continue

                    text = _clean_html(resp.text)
                    snippet = text[:per_page_chars]
                    pages.append(f"### {clean_url}\n{snippet}")
                    total += len(snippet)

                    # Queue internal links if we haven't hit depth limit
                    if depth < max_depth:
                        for link in _extract_links(resp.text, clean_url, allowed_netloc):
                            if link not in visited:
                                queue.append((link, depth + 1))

                except Exception:
                    continue  # skip unreachable pages silently

                if total >= total_chars:
                    break

        if not pages:
            return f"[Could not fetch any content from {start_url}]"

        header = (
            f"Crawled {len(pages)} page(s) from {start_url} "
            f"(domain: {allowed_netloc}, max depth: {max_depth})\n\n"
        )
        return (header + "\n\n".join(pages))[:total_chars + len(header)]

    # --------------------------------------------------------------- Live KT
    def human_explains(self, text: str) -> KTTurn:
        """The human provides an explanation chunk. Returns PULSE's next response."""
        self.state.dialogue_history.append({"role": "human", "text": text})
        prompt = self._build_live_response_prompt()
        response = self._call_model(prompt)
        data = self._parse_json(response)
        return self._apply_turn(data)

    def human_answers(self, answers: Union[Dict[str, str], str]) -> KTTurn:
        """The human answers PULSE's questions. Returns next PULSE response."""
        if isinstance(answers, dict):
            answer_text = "\n".join(f"Q{i+1}: {v}" for i, (_, v) in enumerate(answers.items()))
        else:
            answer_text = answers
        self.state.dialogue_history.append({"role": "human", "text": answer_text})
        prompt = self._build_live_response_prompt()
        response = self._call_model(prompt)
        data = self._parse_json(response)
        return self._apply_turn(data)

    def human_corrects(self, correction: str) -> KTTurn:
        """The human corrects PULSE's summary. Triggers re-synthesis."""
        self.state.dialogue_history.append({"role": "human_correction", "text": correction})
        self.state.confidence_score = max(0.0, self.state.confidence_score - 0.15)
        self.state.phase = KTPhase.LISTENING
        prompt = self._build_live_response_prompt()
        response = self._call_model(prompt)
        data = self._parse_json(response)
        return self._apply_turn(data)

    def _apply_turn(self, data: Dict[str, Any]) -> KTTurn:
        self.state.confidence_score = float(data.get("confidence_score", self.state.confidence_score))
        self.state.mental_model_draft = data.get("mental_model_draft", self.state.mental_model_draft)
        self.state.key_concepts = data.get("key_concepts", self.state.key_concepts)
        new_questions: List[str] = data.get("questions", [])
        self.state.pending_questions = new_questions
        self.state.rounds_completed += 1

        if self.state.confidence_score >= self.confidence_threshold:
            self.state.phase = KTPhase.CONFIRMING
            ready = True
        elif self.state.rounds_completed >= self.max_rounds:
            self.state.phase = KTPhase.SUMMARIZING
            ready = True
        else:
            self.state.phase = KTPhase.QUESTIONING if new_questions else KTPhase.SUMMARIZING
            ready = False

        turn = KTTurn(
            phase=self.state.phase,
            pulse_message=data.get("pulse_message", ""),
            questions=new_questions,
            confidence_score=self.state.confidence_score,
            mental_model_draft=self.state.mental_model_draft,
            ready_to_commit=ready,
        )
        self.state.dialogue_history.append({
            "role": "pulse",
            "text": turn.pulse_message,
            "phase": turn.phase.value,
        })
        return turn

    # -------------------------------------------------------- Summary + Commit
    def generate_summary(self) -> KTSummary:
        """Produce the final KTSummary from current session state."""
        prompt = self._build_summary_prompt()
        response = self._call_model(prompt)
        data = self._parse_json(response)
        return KTSummary(
            session_id=self.session_id,
            session_name=self.state.session_name,
            knowledge_giver=self.knowledge_giver,
            source_type=self.state.source_type,
            mode=self.state.mode,
            key_concepts=data.get("key_concepts", self.state.key_concepts),
            mental_model=data.get("mental_model", self.state.mental_model_draft),
            open_questions=data.get("open_questions", self.state.open_questions),
            connections_to_existing_knowledge=data.get("connections", []),
            confidence_score=self.state.confidence_score,
            rounds_of_dialogue=self.state.rounds_completed,
            domain=data.get("domain", ""),
            tags=data.get("tags", []),
        )

    def commit(self) -> None:
        """Mark the session as committed; caller stores summary to memory."""
        self.state.committed = True
        self.state.phase = KTPhase.COMPLETED

    # --------------------------------------------------------- Prompt builders
    def _build_ingest_prompt(self, source_text: str) -> str:
        name = self.employee.employee_profile.full_name
        role = self.employee.employee_profile.role
        existing_domains = []
        if hasattr(self.employee, "professional_memory"):
            existing_domains = self.employee.professional_memory.get_kt_domains()
        return f"""You are {name} ({role}) reading a document to learn about a new topic.

Session: {self.state.session_name}
Provided by: {self.knowledge_giver}
Existing knowledge domains: {', '.join(existing_domains) or 'none yet'}

Document content:
---
{source_text[:20000]}
---

Build your initial understanding. Respond in JSON:
{{
  "mental_model": "<your understanding of this content in 3-5 sentences>",
  "key_concepts": ["<concept 1>", "<concept 2>", ...],
  "clarifying_questions": ["<question 1>", "<question 2>", ...],
  "confidence_score": <0.0-1.0>,
  "domain": "<primary domain this belongs to>"
}}"""

    def _build_live_response_prompt(self) -> str:
        name = self.employee.employee_profile.full_name
        role = self.employee.employee_profile.role
        history_text = "\n".join(
            f"[{h['role'].upper()}]: {h['text']}"
            for h in self.state.dialogue_history[-20:]
        )
        return f"""You are {name} ({role}) in a live KT session.

Session: {self.state.session_name}
Knowledge giver: {self.knowledge_giver}
Current confidence: {self.state.confidence_score:.0%}
Rounds completed: {self.state.rounds_completed}/{self.max_rounds}
Current mental model: {self.state.mental_model_draft or "still forming"}

Dialogue so far:
{history_text}

Respond as {name}. Your goal: reach ≥{self.confidence_threshold:.0%} confidence by asking targeted questions.

JSON response:
{{
  "pulse_message": "<your next conversational message to the knowledge giver>",
  "questions": ["<specific question 1>", ...],  // empty if confidence reached
  "confidence_score": <updated 0.0-1.0>,
  "mental_model_draft": "<your updated understanding>",
  "key_concepts": ["<concept>", ...]
}}

Rules:
- Ask at most 2-3 focused questions per turn.
- When confidence >= {self.confidence_threshold:.0%}, write a summary of your understanding and set questions to [].
- Be conversational and natural, not robotic.
- Reference specifics from what was said."""

    def _build_summary_prompt(self) -> str:
        name = self.employee.employee_profile.full_name
        history_text = "\n".join(
            f"[{h['role'].upper()}]: {h['text']}"
            for h in self.state.dialogue_history
        )
        return f"""You are {name}. You have completed a KT session on "{self.state.session_name}".

Full dialogue:
{history_text or '[Async source — no dialogue]'}

Current mental model: {self.state.mental_model_draft}
Key concepts identified: {self.state.key_concepts}

Produce a comprehensive KT summary in JSON:
{{
  "mental_model": "<your complete, nuanced understanding in your own words (5-8 sentences)>",
  "key_concepts": ["<concept 1>", ...],
  "open_questions": ["<still unclear question>", ...],
  "connections": ["<how this connects to things you already knew>", ...],
  "domain": "<primary business/technical domain>",
  "tags": ["<tag1>", ...]
}}"""

    # ---------------------------------------------------------- LLM call
    def _call_model(self, prompt: str) -> str:
        """Call the employee's underlying language model."""
        try:
            response = self.employee.run(prompt, stream=False)
            if hasattr(response, "content"):
                return response.content or ""
            return str(response)
        except Exception as e:
            return json.dumps({
                "pulse_message": f"I need to think more about this. ({e})",
                "questions": [],
                "confidence_score": self.state.confidence_score,
                "mental_model_draft": self.state.mental_model_draft,
                "key_concepts": self.state.key_concepts,
                "mental_model": self.state.mental_model_draft,
                "open_questions": [],
                "connections": [],
                "domain": "",
                "tags": [],
                "clarifying_questions": [],
            })

    @staticmethod
    def _parse_json(response: str) -> Dict[str, Any]:
        """Extract JSON from model response, handling markdown fences."""
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        # Find JSON object boundaries
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}


# ---------------------------------------------------------------------------
# KTManager — factory and registry
# ---------------------------------------------------------------------------

class KTManager:
    """Factory and registry for KT sessions of a PULSE employee."""

    def __init__(self, employee: "PulseEmployee") -> None:
        self.employee = employee
        self._sessions: Dict[str, KTSession] = {}
        self._summaries: Dict[str, KTSummary] = {}

    def create_session(
        self,
        session_name: str,
        source_type: KTSourceType,
        knowledge_giver: str,
        confidence_threshold: float = KTSession.CONFIDENCE_THRESHOLD,
        max_rounds: int = KTSession.MAX_ROUNDS,
    ) -> KTSession:
        session = KTSession(
            employee=self.employee,
            session_name=session_name,
            source_type=source_type,
            knowledge_giver=knowledge_giver,
            confidence_threshold=confidence_threshold,
            max_rounds=max_rounds,
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[KTSession]:
        return self._sessions.get(session_id)

    def commit_summary(self, summary: KTSummary) -> None:
        self._summaries[summary.session_id] = summary

    def all_summaries(self) -> List[KTSummary]:
        return list(self._summaries.values())

    def search_knowledge(self, query: str) -> List[KTSummary]:
        query_lower = query.lower()
        results = []
        for s in self._summaries.values():
            if (
                query_lower in s.mental_model.lower()
                or any(query_lower in c.lower() for c in s.key_concepts)
                or query_lower in s.domain.lower()
                or any(query_lower in t.lower() for t in s.tags)
            ):
                results.append(s)
        return results
