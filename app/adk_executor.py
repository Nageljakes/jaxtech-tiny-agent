"""Google ADK adapter that validates every agent's structured response."""

import json
from uuid import uuid4

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import ValidationError

from app.pipeline import (
    feasibility_agent,
    intake_agent,
    mapping_agent,
    ranking_agent,
    risk_agent,
    scoping_agent,
)


class StructuredAdkExecutor:
    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {
            agent.name: agent
            for agent in (
                intake_agent,
                risk_agent,
                feasibility_agent,
                mapping_agent,
                scoping_agent,
                ranking_agent,
            )
        }

    async def _invoke(self, agent: Agent, prompt: str) -> str:
        app_name = f"jaxtech_tiny_{agent.name}"
        runner = InMemoryRunner(agent=agent, app_name=app_name)
        user_id = "synthetic-pipeline"
        session_id = str(uuid4())
        await runner.session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )
        message = types.Content(role="user", parts=[types.Part(text=prompt)])
        reply_parts: list[str] = []
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
        ):
            if event.is_final_response() and event.content:
                reply_parts.extend(
                    part.text for part in event.content.parts or [] if part.text
                )
        if not reply_parts:
            raise RuntimeError(f"{agent.name} returned no final response")
        return "".join(reply_parts)

    async def run(self, agent_name: str, context: dict):
        agent = self._agents.get(agent_name)
        if agent is None:
            raise ValueError(f"Unknown ADK agent: {agent_name}")
        prompt = json.dumps(context, ensure_ascii=False, sort_keys=True)
        response = await self._invoke(agent, prompt)
        schema = agent.output_schema
        if schema is None:
            raise RuntimeError(f"{agent_name} has no output schema")
        try:
            return schema.model_validate_json(response)
        except (ValidationError, ValueError) as error:
            raise ValueError(
                f"{agent_name} did not return valid structured JSON"
            ) from error
