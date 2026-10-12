import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from buddy.media import File, Image
from buddy.models.message import Message
from buddy.utils.log import log_error, log_warning

try:
    from anthropic.types import TextBlock, ToolUseBlock
except ImportError as e:
    raise ImportError("`anthropic` not installed. Please install using `pip install anthropic`") from e


@dataclass
class MCPToolConfiguration:
    enabled: bool = True
    allowed_tools: List[str] = field(default_factory=list)


@dataclass
class MCPServerConfiguration:
    type: str
    url: str
    name: str
    tool_configuration: Optional[MCPToolConfiguration] = None
    authorization_token: Optional[str] = None


ROLE_MAP = {
    "system": "system",
    "user": "user",
    "assistant": "assistant",
    "tool": "user",
}


def _format_image_for_message(image: Image) -> Optional[Dict[str, Any]]:
    """Add an image to a message in Anthropic's content-block format."""
    using_filetype = False
    import base64

    try:
        import imghdr
    except ImportError:
        try:
            import filetype

            using_filetype = True
        except ImportError as e:
            raise ImportError("`filetype` not installed. Please install using `pip install filetype`") from e

    type_mapping = {
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }

    try:
        if image.content is not None and hasattr(image.content, "id"):
            return {"type": "image", "source": {"type": "file", "file_id": image.content.id}}
        if image.url is not None:
            return {"type": "image", "source": {"type": "url", "url": image.url}}
        if image.filepath is not None:
            from pathlib import Path

            path = Path(image.filepath) if isinstance(image.filepath, str) else image.filepath
            if path.exists() and path.is_file():
                content_bytes = path.read_bytes()
            else:
                log_error(f"Image file not found: {image}")
                return None
        elif image.content is not None:
            content_bytes = image.content
        else:
            log_error(f"Unsupported image type: {type(image)}")
            return None

        if using_filetype:
            kind = filetype.guess(content_bytes)
            if not kind:
                log_error("Unable to determine image type")
                return None
            image_type = kind.extension
        else:
            image_type = imghdr.what(None, h=content_bytes)  # type: ignore

        media_type = type_mapping.get(image_type or "")
        if not media_type:
            log_error(f"Unsupported image type: {image_type}")
            return None

        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.b64encode(content_bytes).decode("utf-8"),
            },
        }
    except Exception as e:
        log_error(f"Error processing image: {e}")
        return None


def _format_file_for_message(file: File) -> Optional[Dict[str, Any]]:
    """Add a document URL or base64-encoded content to a message."""
    mime_mapping = {"application/pdf": "base64", "text/plain": "text"}

    if file.external is not None and hasattr(file.external, "id"):
        return {"type": "document", "source": {"type": "file", "file_id": file.external.id}}
    if file.url is not None:
        return {
            "type": "document",
            "source": {"type": "url", "url": file.url},
            "citations": {"enabled": True},
        }
    if file.filepath is not None:
        import base64
        from pathlib import Path

        path = Path(file.filepath) if isinstance(file.filepath, str) else file.filepath
        if not path.exists() or not path.is_file():
            log_error(f"Document file not found: {file}")
            return None
        file_data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
        media_type = file.mime_type
        if media_type is None:
            import mimetypes

            media_type = mimetypes.guess_type(str(file.filepath))[0] or "application/pdf"
        source_type = mime_mapping.get(media_type, "base64")
        return {
            "type": "document",
            "source": {"type": source_type, "media_type": media_type, "data": file_data},
            "citations": {"enabled": True},
        }
    if file.content is not None:
        import base64

        file_data = base64.standard_b64encode(file.content).decode("utf-8")
        return {
            "type": "document",
            "source": {"type": "base64", "media_type": file.mime_type or "application/pdf", "data": file_data},
            "citations": {"enabled": True},
        }
    return None


def format_messages(messages: List[Message]) -> Tuple[List[Dict[str, Any]], str]:
    """Convert framework messages into Anthropic messages and system text."""
    chat_messages: List[Dict[str, Any]] = []
    system_messages: List[str] = []

    for message in messages:
        content: Any = message.content or ""
        if message.role == "system":
            if content is not None:
                system_messages.append(str(content))
            continue
        if message.role == "user":
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            if message.images is not None:
                for image in message.images:
                    image_content = _format_image_for_message(image)
                    if image_content:
                        content.append(image_content)
            if message.files is not None:
                for file in message.files:
                    file_content = _format_file_for_message(file)
                    if file_content:
                        content.append(file_content)
            if message.audio:
                log_warning("Audio input is currently unsupported.")
            if message.videos:
                log_warning("Video input is currently unsupported.")
        elif message.role == "assistant":
            content = []
            if message.thinking is not None and message.provider_data is not None:
                from anthropic.types import ThinkingBlock

                content.append(
                    ThinkingBlock(
                        thinking=message.thinking,
                        signature=message.provider_data.get("signature"),
                        type="thinking",
                    )
                )
            if message.redacted_thinking is not None:
                from anthropic.types import RedactedThinkingBlock

                content.append(RedactedThinkingBlock(data=message.redacted_thinking, type="redacted_thinking"))
            if isinstance(message.content, str) and message.content.strip():
                content.append(TextBlock(text=message.content, type="text"))
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    content.append(
                        ToolUseBlock(
                            id=tool_call["id"],
                            input=json.loads(tool_call["function"]["arguments"])
                            if "arguments" in tool_call["function"]
                            else {},
                            name=tool_call["function"]["name"],
                            type="tool_use",
                        )
                    )

        if message.role == "assistant" and not content:
            continue
        chat_messages.append({"role": ROLE_MAP[message.role], "content": content})

    return chat_messages, " ".join(system_messages)
