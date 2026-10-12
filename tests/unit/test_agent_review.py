import json
from types import SimpleNamespace

from buddy.agent.agent import Agent
from buddy.models.message import Message
from buddy.models.response import ModelResponse
from buddy.run.response import RunResponse


class ReviewModel:
    def __init__(self, responses):
        self.responses = iter(responses)

    def response(self, **kwargs):
        return ModelResponse(content=next(self.responses))


def test_agent_advisor_and_judge_are_configurable():
    model = ReviewModel(["Mention the user's deadline.", '{"passed":true,"score":0.9,"feedback":"Complete."}'])
    agent = Agent(
        model=model,
        advisor=True,
        advisor_config={"instructions": "Give one useful suggestion."},
        judge=True,
        judge_config={"criteria": "Be complete."},
    )
    messages = SimpleNamespace(messages=[Message(role="user", content="Summarize the plan")])

    guidance = agent._apply_advisor(messages)
    response = RunResponse(content="Summary")
    agent._apply_judge(response, messages)

    assert guidance == "Mention the user's deadline."
    assert any(message.content == f"Advisor guidance: {guidance}" for message in messages.messages)
    assert response.judge_result == {"passed": True, "score": 0.9, "feedback": "Complete."}
    assert json.loads(response.to_json())["judge_result"]["passed"] is True
