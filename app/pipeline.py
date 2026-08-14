"""ADK agents for the structured Phase 2 scoping pipeline."""

from google.adk.agents import Agent

from app.agent import MODEL
from app.schemas import FeasibilityResult, IntakeResult, MappingResult

intake_agent = Agent(
    name="intake_agent",
    model=MODEL,
    description="Extracts the actual repetitive workflow from a task submission.",
    instruction=(
        "Analyse only the supplied synthetic task submission. Extract the repetitive "
        "work, named or implied systems, trigger, desired outcome, language, and only "
        "the missing facts required to scope automation. Do not invent integrations, "
        "volumes, permissions, or access. Return IntakeResult exactly. Questions in "
        "missing_information must each request one concrete fact."
    ),
    output_schema=IntakeResult,
    output_key="intake_result",
)

feasibility_agent = Agent(
    name="feasibility_agent",
    model=MODEL,
    description="Classifies whether the extracted workflow can be automated safely.",
    instruction=(
        "Evaluate the synthetic workflow using the intake result in session state. "
        "Classify it as fully automatable, partially automatable, or not safely "
        "automatable. State assumptions, exclusions, a concise rationale, and a "
        "realistic integer development-hour estimate. Never assume vendor permission, "
        "production credentials, consent, or authority. Return FeasibilityResult exactly."
    ),
    output_schema=FeasibilityResult,
    output_key="feasibility_result",
)

mapping_agent = Agent(
    name="mapping_agent",
    model=MODEL,
    description="Maps requirements only to verified Jaxtech catalogue capabilities.",
    instruction=(
        "Map the synthetic intake requirements only against the candidate capability "
        "IDs supplied in session state. For every match, preserve the exact capability "
        "ID, name the concrete external products, APIs, protocols, or devices required, "
        "and explain the fit. Put unsupported needs in unmapped_requirements. Never "
        "invent a capability ID or imply an integration is already authorised or "
        "connected. Return MappingResult exactly."
    ),
    output_schema=MappingResult,
    output_key="mapping_result",
)
