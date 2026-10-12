import json
from types import SimpleNamespace

from buddy.tools.token_manager import TokenManager


def test_custom_token_counter_and_zero_limit():
    manager = TokenManager(token_counter=lambda text: len(text), max_input_tokens=0)
    assert manager._count_tokens("abc") == 3
    assert manager._check_limits(1)["within_limits"] is False
    assert json.loads(manager.get_token_count("abc"))["encoding_method"] == "custom"


def test_tiktoken_backend_is_retained_after_initialization(monkeypatch):
    fake_tiktoken = SimpleNamespace(get_encoding=lambda name: SimpleNamespace(encode=lambda text: list(text)))
    monkeypatch.setitem(__import__("sys").modules, "tiktoken", fake_tiktoken)
    manager = TokenManager(encoding="test")
    assert manager.tiktoken_available is True
    assert manager._count_tokens("abc") == 3


def test_context_window_is_enforced():
    manager = TokenManager(token_counter=lambda text: len(text), max_context_window=3)
    result = manager._check_limits(2, 2)
    assert result["within_limits"] is False
    assert any("context window" in issue for issue in result["violations"])


def test_usage_is_not_double_counted_during_limit_check():
    manager = TokenManager(token_counter=lambda text: len(text), max_total_tokens=5)
    json.loads(manager.track_message_metrics(input_tokens=2, output_tokens=1))
    assert manager.stats.total_tokens == 3
    assert manager._check_limits(1)["within_limits"] is True


def test_usage_hook_reads_provider_dictionary_shapes():
    manager = TokenManager(token_counter=lambda text: len(text))
    manager._post_run_hook(None, {"response_usage": {"prompt_tokens": 4, "completion_tokens": 2}})
    assert manager.stats.total_input_tokens == 4
    assert manager.stats.total_output_tokens == 2


def test_zero_chunk_target_returns_validation_error():
    manager = TokenManager(token_counter=lambda text: len(text))
    result = json.loads(manager.suggest_optimal_chunks("text", target_chunk_tokens=0))
    assert "error" in result
