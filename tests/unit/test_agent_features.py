from threading import Barrier
from types import MethodType, SimpleNamespace

from buddy.agent.agent import Agent
from buddy.models.base import Model
from buddy.models.message import Message
from buddy.models.response import ModelResponse


class ModelSettings:
    def __init__(self):
        self.cache_prompt = False
        self.prompt_cache_config = None
        self.parallel_tool_calls = None
        self.token_budget = None


def test_agent_propagates_cache_and_parallel_settings_to_subagents_and_auxiliary_models():
    primary_model = ModelSettings()
    reasoning_model = ModelSettings()
    reviewer_model = ModelSettings()
    worker_model = ModelSettings()
    worker = Agent(name="worker", model=worker_model)
    agent = Agent(
        model=primary_model,
        reasoning_model=reasoning_model,
        advisor=True,
        advisor_config={"model": reviewer_model},
        cache_prompt=True,
        parallel_tool_calls=True,
        subagents=[worker],
    )

    agent.set_defaults()

    assert agent.team == [worker]
    assert agent.subagents == [worker]
    assert len(agent.deep_copy().subagents) == 1
    for model in (primary_model, reasoning_model, reviewer_model, worker_model):
        assert model.cache_prompt is True
        assert model.prompt_cache_config.enabled is True
        assert model.parallel_tool_calls is True


def test_sync_tool_runner_executes_safe_calls_concurrently():
    barrier = Barrier(2)

    class Runner:
        parallel_tool_calls = True

        def run_function_call(self, function_call, function_call_results, additional_messages=None):
            barrier.wait(timeout=2)
            function_call_results.append(Message(role="tool", content=function_call.name))
            yield ModelResponse(content=function_call.name)

    runner = Runner()
    calls = [
        SimpleNamespace(
            name=f"tool_{index}",
            function=SimpleNamespace(
                name=f"tool_{index}",
                requires_confirmation=False,
                requires_user_input=False,
                external_execution=False,
            ),
        )
        for index in range(2)
    ]
    results = []

    events = list(Model.run_function_calls(runner, calls, results))

    assert [message.content for message in results] == ["tool_0", "tool_1"]
    assert len(events) == 2


def test_runner_keeps_confirmation_calls_on_serial_pause_path():
    class Runner:
        parallel_tool_calls = True

        def run_function_call(self, *args, **kwargs):
            raise AssertionError("confirmation-required tool must not execute")

        def create_tool_call_limit_error_result(self, function_call):
            raise AssertionError("tool call limit should not be reached")

    call = SimpleNamespace(
        call_id="call-1",
        arguments={},
        function=SimpleNamespace(
            name="confirm",
            requires_confirmation=True,
            requires_user_input=False,
            external_execution=False,
            user_input_schema=None,
        ),
    )
    results = []

    events = list(Model.run_function_calls(Runner(), [call, call], results))

    assert len(events) == 2
    assert all(event.event == "ToolCallPaused" for event in events)


def test_openai_chat_receives_parallel_tool_setting():
    from buddy.models.openai import OpenAIChat

    model = OpenAIChat(id="gpt-4o-mini", parallel_tool_calls=True)
    assert model.get_request_params()["parallel_tool_calls"] is True
