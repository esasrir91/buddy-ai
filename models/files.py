"""Files API — upload once, reference by file_id in any request.

Provides a provider-agnostic interface for uploading files and referencing
them by ID in Messages requests.  Two backends are supported:

* **Anthropic Files API** (``/v1/files``): native, works for images, PDFs,
  and any file type accepted by the code execution tool.  Files are stored
  server-side and referenced by ``file_id`` in content blocks.

* **Generic base64 fallback**: when the provider doesn't support a Files API,
  the file is read locally and embedded as a base64 content block on each
  request.  The ``FileRef`` returned by :func:`upload_file` or
  :func:`upload_file_async` transparently switches to the correct encoding.

References
----------
* https://platform.claude.com/docs/en/build-with-claude/files
* https://platform.claude.com/docs/en/build-with-claude/vision
* https://platform.claude.com/docs/en/build-with-claude/pdf-support
"""

from __future__ import annotations

import base64
import mimetypes
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# MIME-type helpers
# ---------------------------------------------------------------------------

_IMAGE_MIME_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "image/bmp", "image/tiff",
}

_PDF_MIME_TYPE = "application/pdf"

_PLAIN_TEXT_MIME_TYPES = {
    "text/plain", "text/markdown", "text/csv",
    "text/html", "text/xml",
}

# File extensions that should be treated as plain text even when MIME is absent
_TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".html", ".xml", ".json", ".yaml", ".yml"}


def _guess_mime(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    if mime:
        return mime
    ext = Path(filename).suffix.lower()
    if ext in _TEXT_EXTENSIONS:
        return "text/plain"
    return "application/octet-stream"


# ---------------------------------------------------------------------------
# FileRef — handle for an uploaded or local file
# ---------------------------------------------------------------------------


@dataclass
class FileRef:
    """A reference to a file that can be included in LLM requests.

    After creating a ``FileRef`` (via :func:`upload_file` or
    :func:`from_path`), call :meth:`as_image_block`, :meth:`as_document_block`,
    or :meth:`as_content_block` to get the appropriate content block for the
    target provider.

    Attributes:
        file_id: Anthropic file ID (set when uploaded via the Files API).
            ``None`` for local / base64 references.
        filename: Original file name.
        media_type: MIME type of the file.
        data_b64: Base64-encoded content (set when no file_id is available).
        size_bytes: File size in bytes.
        provider: Backend that stored the file (``"anthropic"`` or
            ``"local"``).
        metadata: Extra provider-specific metadata.
    """

    filename: str = ""
    media_type: str = "application/octet-stream"
    file_id: Optional[str] = None
    data_b64: Optional[str] = None
    size_bytes: int = 0
    provider: str = "local"
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── Content block builders ────────────────────────────────────────────────

    def as_image_block(self) -> Dict[str, Any]:
        """Return an Anthropic-format image content block."""
        if self.file_id:
            return {
                "type": "image",
                "source": {"type": "file", "file_id": self.file_id},
            }
        if self.data_b64:
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": self.media_type,
                    "data": self.data_b64,
                },
            }
        raise ValueError("FileRef has neither file_id nor base64 data.")

    def as_document_block(
        self,
        title: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return an Anthropic-format document content block (PDF or text)."""
        block: Dict[str, Any] = {"type": "document"}

        if self.file_id:
            block["source"] = {"type": "file", "file_id": self.file_id}
        elif self.data_b64:
            block["source"] = {
                "type": "base64",
                "media_type": self.media_type,
                "data": self.data_b64,
            }
        else:
            raise ValueError("FileRef has neither file_id nor base64 data.")

        if title:
            block["title"] = title
        if context:
            block["context"] = context

        return block

    def as_file_block(self) -> Dict[str, Any]:
        """Return an Anthropic-format file content block for the code execution tool."""
        if self.file_id:
            return {
                "type": "file",
                "source": {"type": "file", "file_id": self.file_id},
            }
        if self.data_b64:
            return {
                "type": "file",
                "source": {
                    "type": "base64",
                    "media_type": self.media_type,
                    "data": self.data_b64,
                },
            }
        raise ValueError("FileRef has neither file_id nor base64 data.")

    def as_content_block(
        self,
        title: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return the most appropriate content block for this file type."""
        if self.media_type in _IMAGE_MIME_TYPES:
            return self.as_image_block()
        if self.media_type == _PDF_MIME_TYPE:
            return self.as_document_block(title=title, context=context)
        if self.media_type in _PLAIN_TEXT_MIME_TYPES:
            return self.as_document_block(title=title, context=context)
        return self.as_file_block()

    def as_openai_image_url(self) -> Dict[str, Any]:
        """Return an OpenAI-format image_url content block."""
        if self.data_b64:
            data_url = f"data:{self.media_type};base64,{self.data_b64}"
            return {"type": "image_url", "image_url": {"url": data_url}}
        if self.file_id:
            # OpenAI doesn't have a native file_id image format; use URL if present
            url = self.metadata.get("url", "")
            return {"type": "image_url", "image_url": {"url": url}}
        raise ValueError("FileRef has neither base64 data nor a URL for OpenAI.")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "media_type": self.media_type,
            "file_id": self.file_id,
            "size_bytes": self.size_bytes,
            "provider": self.provider,
            "has_data": self.data_b64 is not None,
        }


# ---------------------------------------------------------------------------
# Local file → FileRef (base64 path, no upload)
# ---------------------------------------------------------------------------


def from_path(
    path: Union[str, Path],
    media_type: Optional[str] = None,
) -> FileRef:
    """Create a :class:`FileRef` from a local file path (base64-encoded).

    No network call is made; the file is read and embedded as base64.  Use
    :func:`upload_file` to upload to the Anthropic Files API instead.

    Args:
        path: Local file path.
        media_type: Override the auto-detected MIME type.

    Returns:
        :class:`FileRef` with ``data_b64`` set and ``file_id`` as ``None``.
    """
    p = Path(path)
    data = p.read_bytes()
    mime = media_type or _guess_mime(p.name)
    return FileRef(
        filename=p.name,
        media_type=mime,
        data_b64=base64.standard_b64encode(data).decode("utf-8"),
        size_bytes=len(data),
        provider="local",
    )


def from_bytes(
    data: bytes,
    filename: str,
    media_type: Optional[str] = None,
) -> FileRef:
    """Create a :class:`FileRef` from raw bytes (base64-encoded).

    Args:
        data: File content as bytes.
        filename: Display name for the file.
        media_type: Override the auto-detected MIME type.

    Returns:
        :class:`FileRef` with ``data_b64`` set.
    """
    mime = media_type or _guess_mime(filename)
    return FileRef(
        filename=filename,
        media_type=mime,
        data_b64=base64.standard_b64encode(data).decode("utf-8"),
        size_bytes=len(data),
        provider="local",
    )


def from_url(
    url: str,
    media_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Return an Anthropic-format image content block for a URL source.

    Note: URL-sourced images are not uploaded to the Files API; Claude fetches
    them at inference time.  This helper is provided for convenience.
    """
    mime = media_type or "image/jpeg"
    return {
        "type": "image",
        "source": {"type": "url", "url": url},
    }


# ---------------------------------------------------------------------------
# Anthropic Files API — upload
# ---------------------------------------------------------------------------


def upload_file(
    source: Union[str, Path, bytes, BinaryIO],
    filename: Optional[str] = None,
    media_type: Optional[str] = None,
    api_key: Optional[str] = None,
) -> FileRef:
    """Upload a file to the Anthropic Files API.

    Falls back to :func:`from_path` / :func:`from_bytes` when the Anthropic
    package is not available or the API call fails.

    Args:
        source: File path, raw bytes, or an open binary file object.
        filename: Display name for the file (auto-detected from path).
        media_type: Override the auto-detected MIME type.
        api_key: Anthropic API key (falls back to ``ANTHROPIC_API_KEY``).

    Returns:
        :class:`FileRef` with ``file_id`` set (Anthropic) or ``data_b64``
        set (fallback).
    """
    # ── Normalise source ─────────────────────────────────────────────────────
    data: bytes
    fname: str

    if isinstance(source, (str, Path)):
        p = Path(source)
        fname = filename or p.name
        data = p.read_bytes()
    elif isinstance(source, bytes):
        fname = filename or "file"
        data = source
    else:
        fname = filename or getattr(source, "name", "file")
        data = source.read()

    mime = media_type or _guess_mime(fname)

    # ── Try Anthropic Files API ──────────────────────────────────────────────
    try:
        from anthropic import Anthropic
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("No ANTHROPIC_API_KEY")
        client = Anthropic(api_key=key)
        response = client.files.upload(
            file=(fname, data, mime),
        )
        return FileRef(
            filename=fname,
            media_type=mime,
            file_id=str(response.id),
            size_bytes=len(data),
            provider="anthropic",
            metadata={"created_at": getattr(response, "created_at", None)},
        )
    except Exception:
        pass

    # ── Fallback: local base64 ───────────────────────────────────────────────
    return FileRef(
        filename=fname,
        media_type=mime,
        data_b64=base64.standard_b64encode(data).decode("utf-8"),
        size_bytes=len(data),
        provider="local",
    )


async def upload_file_async(
    source: Union[str, Path, bytes, BinaryIO],
    filename: Optional[str] = None,
    media_type: Optional[str] = None,
    api_key: Optional[str] = None,
) -> FileRef:
    """Async variant of :func:`upload_file`."""
    if isinstance(source, (str, Path)):
        p = Path(source)
        fname = filename or p.name
        data = p.read_bytes()
    elif isinstance(source, bytes):
        fname = filename or "file"
        data = source
    else:
        fname = filename or getattr(source, "name", "file")
        data = source.read()

    mime = media_type or _guess_mime(fname)

    try:
        from anthropic import AsyncAnthropic
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("No ANTHROPIC_API_KEY")
        client = AsyncAnthropic(api_key=key)
        response = await client.files.upload(
            file=(fname, data, mime),
        )
        return FileRef(
            filename=fname,
            media_type=mime,
            file_id=str(response.id),
            size_bytes=len(data),
            provider="anthropic",
            metadata={"created_at": getattr(response, "created_at", None)},
        )
    except Exception:
        pass

    return FileRef(
        filename=fname,
        media_type=mime,
        data_b64=base64.standard_b64encode(data).decode("utf-8"),
        size_bytes=len(data),
        provider="local",
    )


# ---------------------------------------------------------------------------
# Anthropic Files API — management
# ---------------------------------------------------------------------------


def list_files(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all files in the Anthropic workspace.

    Returns a list of dicts with ``id``, ``filename``, ``created_at``,
    ``size``.  Returns ``[]`` when the API is unavailable.
    """
    try:
        from anthropic import Anthropic
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            return []
        client = Anthropic(api_key=key)
        page = client.files.list()
        return [
            {
                "id": f.id,
                "filename": getattr(f, "filename", ""),
                "created_at": getattr(f, "created_at", None),
                "size": getattr(f, "size", None),
            }
            for f in (page.data if hasattr(page, "data") else page)
        ]
    except Exception:
        return []


def delete_file(file_id: str, api_key: Optional[str] = None) -> bool:
    """Delete a file from the Anthropic workspace.

    Returns ``True`` on success, ``False`` otherwise.
    """
    try:
        from anthropic import Anthropic
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            return False
        client = Anthropic(api_key=key)
        client.files.delete(file_id)
        return True
    except Exception:
        return False


def download_file(
    file_id: str,
    dest_path: Optional[Union[str, Path]] = None,
    api_key: Optional[str] = None,
) -> bytes:
    """Download a file from the Anthropic workspace.

    Args:
        file_id: The ``file_id`` returned by the Files API.
        dest_path: Optional path to write the file to.
        api_key: Anthropic API key.

    Returns:
        The raw file bytes.
    """
    try:
        from anthropic import Anthropic
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("No ANTHROPIC_API_KEY")
        client = Anthropic(api_key=key)
        response = client.files.retrieve_content(file_id)
        data = response.content if hasattr(response, "content") else bytes(response)
        if dest_path:
            Path(dest_path).write_bytes(data)
        return data
    except Exception as exc:
        raise RuntimeError(f"Failed to download file {file_id!r}: {exc}") from exc


# ---------------------------------------------------------------------------
# OpenAI Files API helpers (for consistency)
# ---------------------------------------------------------------------------


def upload_file_openai(
    source: Union[str, Path, bytes],
    filename: Optional[str] = None,
    purpose: str = "assistants",
    api_key: Optional[str] = None,
) -> FileRef:
    """Upload a file via the OpenAI Files API.

    Args:
        source: File path or raw bytes.
        filename: Display name.
        purpose: OpenAI file purpose (``"assistants"``, ``"fine-tune"``,
            ``"batch"``).
        api_key: OpenAI API key (falls back to ``OPENAI_API_KEY``).

    Returns:
        :class:`FileRef` with ``file_id`` set and ``provider="openai"``.
    """
    if isinstance(source, (str, Path)):
        p = Path(source)
        fname = filename or p.name
        data = p.read_bytes()
    else:
        fname = filename or "file"
        data = source

    mime = _guess_mime(fname)

    try:
        import openai
        key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("No OPENAI_API_KEY")
        client = openai.OpenAI(api_key=key)
        response = client.files.create(
            file=(fname, data, mime),
            purpose=purpose,
        )
        return FileRef(
            filename=fname,
            media_type=mime,
            file_id=str(response.id),
            size_bytes=len(data),
            provider="openai",
        )
    except Exception:
        return FileRef(
            filename=fname,
            media_type=mime,
            data_b64=base64.standard_b64encode(data).decode("utf-8"),
            size_bytes=len(data),
            provider="local",
        )
