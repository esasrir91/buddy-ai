__all__ = [
    'Model',
    'EffortConfig',
    'ThinkingConfig',
    'FastModeConfig',
    'MultilingualConfig',
    'CitationConfig',
    'SearchResult',
    'DocumentBlock',
    'AnthropicBatchProcessor',
    'OpenAIBatchProcessor',
    'BatchRunner',
    'BatchResult',
    'TokenBudgetConfig',
    'PromptCacheConfig',
    # Thinking convenience constructors
    'adaptive',
    'extended',
    'disabled',
    'omitted',
    # Multilingual convenience constructors
    'always_respond_in',
    'translate',
    # ── Context window ────────────────────────────────────────────────────────
    'ContextWindowConfig',
    'ContextUsage',
    'ContextWindowOverflow',
    'context_window_for_model',
    'max_output_tokens_for_model',
    'is_context_aware',
    'estimate_messages_tokens',
    # ── Compaction ────────────────────────────────────────────────────────────
    'CompactionConfig',
    'CompactionStrategy',
    'CompactionResult',
    'auto_compact',
    'server_compact',
    'client_compact',
    # ── Context editing ───────────────────────────────────────────────────────
    'ContextEditingConfig',
    'clear_tool_results',
    'clear_thinking_blocks',
    'truncate_messages',
    'light_editing',
    'moderate_editing',
    'aggressive_editing',
    # ── Cache diagnostics ─────────────────────────────────────────────────────
    'CacheMetrics',
    'CacheDiagnostics',
    'extract_cache_metrics_anthropic',
    'extract_cache_metrics_openai',
    'extract_cache_metrics_generic',
    # ── Token counting ────────────────────────────────────────────────────────
    'TokenCountResult',
    'count_tokens',
    'count_tokens_async',
    'fits_in_context',
    'estimate_tokens_heuristic',
    # ── Mid-conversation ──────────────────────────────────────────────────────
    'MidConversationPatch',
    'make_system_message',
    'inject_system_message',
    'make_tool_change_message',
    'inject_tool_changes',
    # ── Files API ─────────────────────────────────────────────────────────────
    'FileRef',
    'from_path',
    'from_bytes',
    'from_url',
    'upload_file',
    'upload_file_async',
    'list_files',
    'delete_file',
    'download_file',
    # ── Vision coordinates ────────────────────────────────────────────────────
    'BoundingBox',
    'ResolutionTier',
    'STANDARD_TIER',
    'HIGH_RESOLUTION_TIER',
    'compute_resized_size',
    'compute_resized_size_for_model',
    'count_image_tokens',
    'rescale_coordinates',
    'rescale_bbox',
    'rescale_bboxes',
    'resize_image_to_claude_size',
    'BBOX_SCHEMA',
    'COORDINATE_PROMPT',
    # ── Agent Skills ──────────────────────────────────────────────────────────
    'Skill',
    'SkillRegistry',
    'skill',
    'skill_from_directory',
    'upload_skill',
    'upload_skill_async',
    'list_remote_skills',
    'get_anthropic_skill',
    'ANTHROPIC_SKILLS',
]


def __getattr__(name: str):
    """Lazy-load modules to break buddy.run.* circular import chain."""
    if name == 'Model':
        from buddy.models.base import Model
        return Model
    if name == 'EffortConfig':
        from buddy.models.effort import EffortConfig
        return EffortConfig
    if name in ('ThinkingConfig', 'adaptive', 'extended', 'disabled', 'omitted'):
        import buddy.models.thinking as _thinking
        return getattr(_thinking, name)
    if name == 'FastModeConfig':
        from buddy.models.fast_mode import FastModeConfig
        return FastModeConfig
    if name in ('MultilingualConfig', 'always_respond_in', 'translate'):
        import buddy.models.multilingual as _ml
        return getattr(_ml, name)
    if name in ('CitationConfig', 'SearchResult', 'DocumentBlock'):
        import buddy.models.citations as _cit
        return getattr(_cit, name)
    if name in ('AnthropicBatchProcessor', 'OpenAIBatchProcessor', 'BatchRunner', 'BatchResult'):
        import buddy.models.batch as _batch
        return getattr(_batch, name)
    if name == 'TokenBudgetConfig':
        from buddy.models.token_budget import TokenBudgetConfig
        return TokenBudgetConfig
    if name == 'PromptCacheConfig':
        from buddy.models.cache import PromptCacheConfig
        return PromptCacheConfig

    # ── Context window ────────────────────────────────────────────────────────
    if name in (
        'ContextWindowConfig', 'ContextUsage', 'ContextWindowOverflow',
        'context_window_for_model', 'max_output_tokens_for_model',
        'is_context_aware', 'estimate_messages_tokens',
        'build_context_awareness_system_prefix', 'build_context_warning_block',
        'check_overflow', 'update_usage_from_response',
    ):
        import buddy.models.context_window as _cw
        return getattr(_cw, name)

    # ── Compaction ────────────────────────────────────────────────────────────
    # Canonical location: buddy.agent.compaction
    if name in (
        'CompactionConfig', 'CompactionStrategy', 'CompactionResult',
        'auto_compact', 'server_compact', 'client_compact',
        'compact_messages_async', 'compact_messages_sync',
        'build_summarization_messages', 'build_summary_message',
        'extract_compaction_summary', 'supports_server_compaction',
    ):
        import buddy.agent.compaction as _comp
        return getattr(_comp, name)

    # ── Context editing ───────────────────────────────────────────────────────
    # Canonical location: buddy.agent.context_editing
    if name in (
        'ContextEditingConfig',
        'clear_tool_results', 'clear_thinking_blocks', 'truncate_messages',
        'replace_content_blocks',
        'light_editing', 'moderate_editing', 'aggressive_editing',
        'truncate_agent_messages', 'clear_agent_tool_results',
        'clear_agent_thinking_blocks', 'clear_agent_images',
    ):
        import buddy.agent.context_editing as _ce
        return getattr(_ce, name)

    # ── Cache diagnostics ─────────────────────────────────────────────────────
    if name in (
        'CacheMetrics', 'CacheDiagnostics',
        'extract_cache_metrics_anthropic', 'extract_cache_metrics_openai',
        'extract_cache_metrics_generic',
    ):
        import buddy.models.cache_diagnostics as _cd
        return getattr(_cd, name)

    # ── Token counting ────────────────────────────────────────────────────────
    if name in (
        'TokenCountResult', 'count_tokens', 'count_tokens_async',
        'fits_in_context', 'estimate_tokens_heuristic',
        'estimate_tokens_tiktoken', 'count_tokens_anthropic',
        'count_tokens_anthropic_async',
    ):
        import buddy.models.token_counter as _tc
        return getattr(_tc, name)

    # ── Mid-conversation ──────────────────────────────────────────────────────
    if name in (
        'MidConversationPatch',
        'make_system_message', 'inject_system_message',
        'make_tool_change_message', 'inject_tool_changes',
        'make_tool_addition_block', 'make_tool_removal_block',
        'make_effort_hint_message', 'make_thinking_mode_message',
        'supports_mid_conversation_system', 'supports_mid_conversation_tool_changes',
    ):
        import buddy.models.mid_conversation as _mc
        return getattr(_mc, name)

    # ── Files API ─────────────────────────────────────────────────────────────
    if name in (
        'FileRef', 'from_path', 'from_bytes', 'from_url',
        'upload_file', 'upload_file_async',
        'list_files', 'delete_file', 'download_file',
        'upload_file_openai',
    ):
        import buddy.models.files as _files
        return getattr(_files, name)

    # ── Vision coordinates ────────────────────────────────────────────────────
    if name in (
        'BoundingBox', 'ResolutionTier', 'STANDARD_TIER', 'HIGH_RESOLUTION_TIER',
        'compute_resized_size', 'compute_resized_size_for_model',
        'compute_padded_size', 'count_image_tokens',
        'rescale_coordinates', 'rescale_bbox', 'rescale_bboxes',
        'resize_image_to_claude_size',
        'BBOX_SCHEMA', 'BBOX_LIST_SCHEMA', 'POINT_SCHEMA', 'COORDINATE_PROMPT',
        'resolution_tier_for_model',
    ):
        import buddy.models.vision_coordinates as _vc
        return getattr(_vc, name)

    # ── Agent Skills ──────────────────────────────────────────────────────────
    if name in (
        'Skill', 'SkillRegistry',
        'skill', 'skill_from_directory',
        'upload_skill', 'upload_skill_async',
        'list_remote_skills', 'get_anthropic_skill',
        'ANTHROPIC_SKILLS',
    ):
        import buddy.models.skills as _skills
        return getattr(_skills, name)

    raise AttributeError(f"module 'buddy.models' has no attribute {name!r}")