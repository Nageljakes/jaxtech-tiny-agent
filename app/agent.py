"""Jaxtech Tiny Phase 1 ADK agent."""

from google.adk.agents import Agent

MODEL = "gemini-3.5-flash-lite"

root_agent = Agent(
    name="tiny_stack_proof",
    model=MODEL,
    description="Proves Jaxtech Tiny runs on Google ADK and Gemini.",
    instruction=(
        "You are Tiny, Jaxtech's scoping agent. This is the Phase 1 stack proof. "
        "Reply in one concise sentence, explicitly stating that Google ADK and "
        "Gemini 3.5 are connected. Do not claim that later scoping features exist."
    ),
)
