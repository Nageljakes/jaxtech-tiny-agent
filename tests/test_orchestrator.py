import asyncio

import pytest

from app.domain import RiskAssessment, RiskDecision, RiskFlag
from app.orchestrator import ScopingOrchestrator
from app.repository import InMemoryWorkflowRepository
from app.schemas import (
    ArchitectureComponent,
    AutomationLevel,
    CapabilityMatch,
    FeasibilityResult,
    IntakeResult,
    MappingResult,
    RankingAssessment,
    ScopePack,
)
from app.workflow import PipelineStage


class FakeExecutor:
    def __init__(self, risk_decision: RiskDecision = RiskDecision.CLEAR) -> None:
        self.calls: list[str] = []
        self.outputs = {
            "intake_agent": IntakeResult(
                repetitive_work=["Copy synthetic form rows"],
                systems=["Synthetic form", "Demo spreadsheet"],
                trigger="Synthetic form submitted",
                desired_outcome="Validated demo tracking row",
                missing_information=[],
                language="en-ZA",
            ),
            "risk_agent": RiskAssessment(
                decision=risk_decision,
                flags=[] if risk_decision is RiskDecision.CLEAR else [RiskFlag.PHYSICAL_SAFETY],
                reasons=["Synthetic risk assessment"],
            ),
            "feasibility_agent": FeasibilityResult(
                level=AutomationLevel.FULL,
                rationale="Synthetic administrative transfer is feasible.",
                assumptions=["Stable synthetic schema"],
                exclusions=["No production personal data"],
                estimated_development_hours=12,
            ),
            "mapping_agent": MappingResult(
                matches=[
                    CapabilityMatch(
                        capability_id="xlsx",
                        integrations=["Google Sheets API"],
                        rationale="Writes structured spreadsheet rows.",
                    )
                ],
                unmapped_requirements=[],
            ),
            "scoping_agent": ScopePack(
                problem="Synthetic rows are copied manually.",
                proposed_workflow=["Receive", "Validate", "Write"],
                architecture=[
                    ArchitectureComponent(
                        name="Worker",
                        responsibility="Orchestrate synthetic transfer",
                        technology="Cloud Run",
                    )
                ],
                integrations=["Google Sheets API"],
                estimated_development_hours=12,
                assumptions=["Stable synthetic schema"],
                exclusions=["No production personal data"],
                open_questions=[],
            ),
            "ranking_agent": RankingAssessment(
                usefulness=8,
                feasibility=9,
                interest=7,
                justification="Useful and feasible synthetic workflow.",
            ),
        }

    async def run(self, agent_name: str, context: dict):
        self.calls.append(agent_name)
        return self.outputs[agent_name]


def test_complete_pipeline_runs_in_order_and_persists_ranked_state() -> None:
    executor = FakeExecutor()
    repository = InMemoryWorkflowRepository()
    orchestrator = ScopingOrchestrator(repository, executor)

    result = asyncio.run(
        orchestrator.run("syn-001", "Put synthetic form submissions into Excel")
    )

    assert executor.calls == [
        "intake_agent",
        "risk_agent",
        "feasibility_agent",
        "mapping_agent",
        "scoping_agent",
        "ranking_agent",
    ]
    assert result.stage is PipelineStage.RANKED
    assert result.revision == 6
    assert result.artifacts["ranked"]["weighted_total"] == 8.2
    assert repository.load("syn-001") == result


def test_risk_veto_stops_all_downstream_agents() -> None:
    executor = FakeExecutor(RiskDecision.VETO)
    orchestrator = ScopingOrchestrator(InMemoryWorkflowRepository(), executor)

    result = asyncio.run(
        orchestrator.run("syn-unsafe", "Synthetic safety-critical control")
    )

    assert executor.calls == ["intake_agent", "risk_agent"]
    assert result.stage is PipelineStage.VETOED
    assert "feasibility_complete" not in result.artifacts


def test_completed_pipeline_replay_is_idempotent_and_makes_no_agent_calls() -> None:
    repository = InMemoryWorkflowRepository()
    first_executor = FakeExecutor()
    first = asyncio.run(
        ScopingOrchestrator(repository, first_executor).run(
            "syn-001", "Put synthetic form submissions into Excel"
        )
    )
    replay_executor = FakeExecutor()

    replay = asyncio.run(
        ScopingOrchestrator(repository, replay_executor).run(
            "syn-001", "Put synthetic form submissions into Excel"
        )
    )

    assert replay == first
    assert replay_executor.calls == []


def test_review_decision_stops_before_downstream_agents() -> None:
    executor = FakeExecutor(RiskDecision.REVIEW)
    orchestrator = ScopingOrchestrator(InMemoryWorkflowRepository(), executor)

    result = asyncio.run(
        orchestrator.run("syn-review", "Synthetic workflow requiring approval")
    )

    assert executor.calls == ["intake_agent", "risk_agent"]
    assert result.stage is PipelineStage.REVIEW_REQUIRED


def test_pipeline_resumes_after_failure_from_last_persisted_boundary() -> None:
    class FailingExecutor(FakeExecutor):
        async def run(self, agent_name: str, context: dict):
            if agent_name == "mapping_agent":
                self.calls.append(agent_name)
                raise RuntimeError("synthetic transient failure")
            return await super().run(agent_name, context)

    repository = InMemoryWorkflowRepository()
    failing = FailingExecutor()
    orchestrator = ScopingOrchestrator(repository, failing)

    with pytest.raises(RuntimeError, match="synthetic transient failure"):
        asyncio.run(
            orchestrator.run("syn-resume", "Put synthetic submissions into Excel")
        )

    persisted = repository.load("syn-resume")
    assert persisted is not None
    assert persisted.stage is PipelineStage.FEASIBILITY_COMPLETE

    resumed_executor = FakeExecutor()
    result = asyncio.run(
        ScopingOrchestrator(repository, resumed_executor).run(
            "syn-resume", "Put synthetic submissions into Excel"
        )
    )

    assert resumed_executor.calls == ["mapping_agent", "scoping_agent", "ranking_agent"]
    assert result.stage is PipelineStage.RANKED
