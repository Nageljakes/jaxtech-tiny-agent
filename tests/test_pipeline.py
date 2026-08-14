from app.agent import MODEL
from app.pipeline import feasibility_agent, intake_agent, mapping_agent
from app.schemas import AutomationLevel, FeasibilityResult, IntakeResult, MappingResult


def test_intake_schema_captures_scoping_facts_and_missing_questions() -> None:
    result = IntakeResult(
        repetitive_work=["Copy synthetic web leads into a demo tracker"],
        systems=["Synthetic website", "Demo spreadsheet"],
        trigger="A synthetic form is submitted",
        desired_outcome="A complete demo tracking row",
        missing_information=["Expected synthetic submissions per day"],
        language="en-ZA",
    )

    assert result.is_complete is False
    assert result.missing_information == ["Expected synthetic submissions per day"]


def test_intake_is_complete_when_no_information_is_missing() -> None:
    result = IntakeResult(
        repetitive_work=["Copy synthetic web leads into a demo tracker"],
        systems=["Synthetic website", "Demo spreadsheet"],
        trigger="A synthetic form is submitted",
        desired_outcome="A complete demo tracking row",
        missing_information=[],
        language="en-ZA",
    )

    assert result.is_complete is True


def test_feasibility_schema_requires_assumptions_and_exclusions() -> None:
    result = FeasibilityResult(
        level=AutomationLevel.PARTIAL,
        rationale="Synthetic records can be transferred automatically, with review for malformed input.",
        assumptions=["The synthetic form schema remains stable"],
        exclusions=["No production customer records"],
        estimated_development_hours=12,
    )

    assert result.level is AutomationLevel.PARTIAL
    assert result.estimated_development_hours == 12


def test_adk_agents_use_required_model_and_structured_outputs() -> None:
    assert intake_agent.model == MODEL == "gemini-3.5-flash-lite"
    assert intake_agent.output_schema is IntakeResult
    assert intake_agent.output_key == "intake_result"
    assert feasibility_agent.model == MODEL
    assert feasibility_agent.output_schema is FeasibilityResult
    assert feasibility_agent.output_key == "feasibility_result"
    assert mapping_agent.model == MODEL
    assert mapping_agent.output_schema is MappingResult
    assert mapping_agent.output_key == "mapping_result"
