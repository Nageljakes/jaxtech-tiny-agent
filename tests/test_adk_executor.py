import asyncio

import pytest

from app.adk_executor import StructuredAdkExecutor
from app.schemas import IntakeResult


class StubExecutor(StructuredAdkExecutor):
    def __init__(self, response: str) -> None:
        super().__init__()
        self.response = response
        self.seen_prompt = ""

    async def _invoke(self, agent, prompt: str) -> str:
        self.seen_prompt = prompt
        return self.response


def test_structured_executor_parses_agent_output_schema() -> None:
    executor = StubExecutor(
        """{"repetitive_work":["Copy synthetic rows"],"systems":["Demo form","Demo sheet"],"trigger":"Synthetic submit","desired_outcome":"Tracked row","missing_information":[],"language":"en-ZA"}"""
    )

    result = asyncio.run(
        executor.run(
            "intake_agent",
            {"task_description": "Synthetic task", "synthetic": True},
        )
    )

    assert isinstance(result, IntakeResult)
    assert result.desired_outcome == "Tracked row"
    assert '"synthetic": true' in executor.seen_prompt


def test_structured_executor_rejects_unknown_agent() -> None:
    executor = StubExecutor("{}")

    with pytest.raises(ValueError, match="Unknown ADK agent"):
        asyncio.run(executor.run("invented_agent", {}))


def test_structured_executor_fails_closed_on_markdown_or_invalid_json() -> None:
    executor = StubExecutor("```json\n{}\n```")

    with pytest.raises(ValueError, match="valid structured JSON"):
        asyncio.run(executor.run("intake_agent", {"synthetic": True}))
