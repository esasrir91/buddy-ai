"""Backward-compatibility shim.

The canonical implementation has moved to :mod:`buddy.agent.compaction`
where it belongs architecturally — compaction manages the *agent's*
conversation history lifecycle, not the model's inference parameters.

All public names are re-exported here so that existing code that imports
from ``buddy.models.compaction`` continues to work unchanged.
"""

from buddy.agent.compaction import (  # noqa: F401
    CompactionConfig,
    CompactionResult,
    CompactionStrategy,
    auto_compact,
    build_summarization_messages,
    build_summary_message,
    client_compact,
    compact_messages_async,
    compact_messages_sync,
    extract_compaction_summary,
    server_compact,
    supports_server_compaction,
)

__all__ = [
    "CompactionConfig",
    "CompactionStrategy",
    "CompactionResult",
    "auto_compact",
    "server_compact",
    "client_compact",
    "supports_server_compaction",
    "build_summarization_messages",
    "build_summary_message",
    "extract_compaction_summary",
    "compact_messages_async",
    "compact_messages_sync",
]
