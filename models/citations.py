"""Citation configuration and search result content blocks.

This module provides:

1. **CitationConfig** – per-document citation settings (enable/disable, format).
2. **SearchResult** – a structured content block for RAG applications.
   Claude cites search results with source attribution automatically when
   ``citations.enabled=True``.
3. **DocumentBlock** – helper to build plain-text / PDF / custom-content
   document blocks for the Anthropic Citations API.

Claude-native citations
-----------------------
When ``citations.enabled=True`` on a document block, Claude returns
interleaved ``text`` and ``citation`` content blocks.  Each citation
carries ``cited_text`` (not billed as output tokens), ``document_index``,
and format-specific location fields:

* **Plain text** → ``char_location`` (start/end character indices)
* **PDF**        → ``page_location`` (1-indexed page numbers)
* **Custom**     → ``content_block_location`` (block indices)

Compatibility note
------------------
Citations and structured outputs (``output_config.format``) are mutually
exclusive on the Anthropic API.  ``CitationConfig`` raises a warning if
both are enabled on the same request.

For non-Claude models, search results are formatted as plain text injected
into the context, and a prompt instruction is added to cite sources.

References
----------
* https://platform.claude.com/docs/en/build-with-claude/citations
* https://platform.claude.com/docs/en/build-with-claude/search-results
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


DocumentType = Literal["text", "pdf", "custom"]
CitationFormat = Literal["char_location", "page_location", "content_block_location"]


@dataclass
class CitationConfig:
    """Per-request citation configuration.

    Attributes:
        enabled: Enable Claude's native citation feature.  When ``True``,
            all document/search-result blocks in the request must have
            ``citations.enabled=True`` (all-or-none rule).
        inject_prompt: For non-Claude models, prepend a citation instruction
            to the system prompt when ``enabled=True``.
    """

    enabled: bool = True
    inject_prompt: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {"enabled": self.enabled}

    def to_prompt_hint(self, sources: Optional[List[str]] = None) -> str:
        """Return a system-prompt instruction for models without native citation support."""
        if not self.enabled or not self.inject_prompt:
            return ""
        base = (
            "When answering, always cite the specific sources you draw from. "
            "Include the source name or URL in square brackets, e.g. [Source Title]."
        )
        if sources:
            source_list = "\n".join(f"- {s}" for s in sources)
            base += f"\n\nAvailable sources:\n{source_list}"
        return base


@dataclass
class SearchResult:
    """A RAG search result provided to the model as a first-class content block.

    Claude cites search results automatically when ``citations_enabled=True``.
    For other models, the content is serialised as formatted text.

    Attributes:
        source: Required.  A URL or stable identifier (e.g. ``"kb://doc-123"``).
        title: Required.  A descriptive title for the result.
        content: The text content.  Passed as a list of text blocks.
        citations_enabled: Enable citation attribution for this result.
        cache_control: Optional Anthropic prompt-cache control dict,
            e.g. ``{"type": "ephemeral"}``.
    """

    source: str
    title: str
    content: str
    citations_enabled: bool = True
    cache_control: Optional[Dict[str, Any]] = None

    def to_anthropic_block(self) -> Dict[str, Any]:
        """Serialise to the ``search_result`` content block format."""
        block: Dict[str, Any] = {
            "type": "search_result",
            "source": self.source,
            "title": self.title,
            "content": [{"type": "text", "text": self.content}],
            "citations": {"enabled": self.citations_enabled},
        }
        if self.cache_control:
            block["cache_control"] = self.cache_control
        return block

    def to_text(self) -> str:
        """Plain-text representation for non-Claude models."""
        return f"[{self.title}] ({self.source})\n{self.content}"


@dataclass
class DocumentBlock:
    """A document passed to Claude for citations.

    Attributes:
        content: Text content (for plain-text documents) or a list of dicts
            (for custom-content documents).
        doc_type: ``"text"`` | ``"pdf"`` | ``"custom"``.
        title: Optional document title (not citable).
        context: Optional metadata / context string (not citable).
        citations_enabled: Enable citations for this document.
        cache_control: Optional Anthropic cache-control dict.
        file_id: File ID from the Files API (alternative to inline content).
        url: URL for URL-referenced PDFs.
        media_type: MIME type for base64/URL sources.
    """

    content: Any = ""
    doc_type: DocumentType = "text"
    title: Optional[str] = None
    context: Optional[str] = None
    citations_enabled: bool = True
    cache_control: Optional[Dict[str, Any]] = None
    file_id: Optional[str] = None
    url: Optional[str] = None
    media_type: str = "text/plain"

    def to_anthropic_block(self) -> Dict[str, Any]:
        """Serialise to the Anthropic API ``document`` content block format."""
        block: Dict[str, Any] = {"type": "document"}

        if self.file_id:
            block["source"] = {"type": "file", "file_id": self.file_id}
        elif self.url:
            block["source"] = {"type": "url", "url": self.url}
        elif self.doc_type == "custom":
            chunks = self.content if isinstance(self.content, list) else [self.content]
            block["source"] = {
                "type": "content",
                "content": [
                    {"type": "text", "text": c} if isinstance(c, str) else c
                    for c in chunks
                ],
            }
        else:
            # plain text or pdf inline
            block["source"] = {
                "type": "text",
                "media_type": self.media_type,
                "data": self.content if isinstance(self.content, str) else str(self.content),
            }

        if self.title:
            block["title"] = self.title
        if self.context:
            block["context"] = self.context
        block["citations"] = {"enabled": self.citations_enabled}
        if self.cache_control:
            block["cache_control"] = self.cache_control

        return block

    def to_text(self) -> str:
        """Plain text for non-Claude models."""
        header = f"[{self.title}]" if self.title else "[Document]"
        body = self.content if isinstance(self.content, str) else str(self.content)
        return f"{header}\n{body}"


def parse_citation_blocks(response_content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract citation information from an Anthropic API response content list.

    Returns a list of dicts with keys:
        ``text``       – the claim text
        ``citations``  – list of citation dicts (char_location / page_location / content_block_location)
    """
    results = []
    for block in response_content:
        if block.get("type") != "text":
            continue
        citations = block.get("citations")
        if citations:
            results.append({"text": block.get("text", ""), "citations": citations})
    return results
