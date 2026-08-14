"""ADK agents for the structured Phase 2 scoping pipeline."""

from google.adk.agents import Agent

from app.agent import MODEL
from app.domain import RiskAssessment
from app.schemas import (
    FeasibilityResult,
    IntakeResult,
    MappingResult,
    RankingAssessment,
    ScopePack,
)

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

risk_agent = Agent(
    name="risk_agent",
    model=MODEL,
    description="Issues a binding safety, legality, privacy, and vendor-terms decision.",
    instruction=(
        "Review the synthetic intake result for POPIA or personal-data exposure, vendor "
        "terms, money movement, physical safety, illegality, and cybersecurity abuse. "
        "Return clear only when downstream scoping may safely continue, review when "
        "accountable human approval is required, and veto when the requested automation "
        "is unsafe or unlawful. A veto is binding. Return RiskAssessment exactly."
    ),
    output_schema=RiskAssessment,
    output_key="risk_assessment",
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

scoping_agent = Agent(
    name="scoping_agent",
    model=MODEL,
    description="Produces the decision-ready written scope pack.",
    instruction=(
        "Using only validated intake, feasibility, risk, and catalogue mapping state, "
        "produce a complete written scope pack. Include the problem, ordered workflow, "
        "agent architecture with named technologies and responsibilities, concrete "
        "integrations, development hours, assumptions, exclusions, and open questions. "
        "Do not remove risk exclusions or claim access is authorised. Return ScopePack "
        "exactly."
    ),
    output_schema=ScopePack,
    output_key="scope_pack",
)

ranking_agent = Agent(
    name="ranking_agent",
    model=MODEL,
    description="Assesses usefulness, feasibility, and interest on explicit scales.",
    instruction=(
        "Assess the synthetic scope pack from 0 to 10 on usefulness, feasibility, and "
        "interest. Usefulness means recurring human effort and operational value; "
        "feasibility means technical, permission, safety, and delivery realism; interest "
        "means demonstration value and distinctiveness. Give a concise evidence-based "
        "justification. Do not calculate a total or rank; deterministic code does that. "
        "Return RankingAssessment exactly."
    ),
    output_schema=RankingAssessment,
    output_key="ranking_assessment",
)
