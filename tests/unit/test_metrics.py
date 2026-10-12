from buddy.agent.metrics import SessionMetrics
from buddy.models.message import MessageMetrics


def test_time_to_first_token_preserves_zero():
    metrics = SessionMetrics(time_to_first_token=0.0) + MessageMetrics(time_to_first_token=1.0)
    message_metrics = MessageMetrics(time_to_first_token=0.0) + MessageMetrics(time_to_first_token=1.0)

    assert metrics.time_to_first_token == 0.0
    assert message_metrics.time_to_first_token == 0.0


def test_to_dict_excludes_runtime_timer():
    metrics = SessionMetrics()
    metrics.start_timer()

    serialized = metrics.to_dict()
    restored = SessionMetrics(**serialized)

    assert "timer" not in serialized
    assert restored.timer is None

    restored.start_timer()
    restored.stop_timer()
    assert restored.time is not None