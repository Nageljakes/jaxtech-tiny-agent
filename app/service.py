"""Google ADK execution adapter for the Phase 1 proof."""

from uuid import uuid4

from google.adk.runners import InMemoryRunner
from google.genai import types

from app.agent import root_agent


class AgentService:
    """Run one isolated ADK session per proof request."""

    def __init__(self) -> None:
        self._runner = InMemoryRunner(agent=root_agent, app_name="jaxtech_tiny")

    async def prove(self, message: str) -> str:
        user_id = "phase-one-visitor"
        session_id = str(uuid4())
        await self._runner.session_service.create_session(
            app_name="jaxtech_tiny",
            user_id=user_id,
            session_id=session_id,
        )
        content = types.Content(role="user", parts=[types.Part(text=message)])
        reply_parts: list[str] = []
        async for event in self._runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response() and event.content:
                reply_parts.extend(
                    part.text for part in event.content.parts or [] if part.text
                )
        if not reply_parts:
            raise RuntimeError("Gemini returned no final text response")
        return "".join(reply_parts)
