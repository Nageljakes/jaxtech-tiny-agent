"""Crash-resumable orchestration across the structured ADK agent stages."""

from typing import Any, Protocol

from app.catalog import candidate_capabilities, validate_mapping
from app.domain import RiskAssessment, RiskDecision
from app.schemas import (
    FeasibilityResult,
    IntakeResult,
    MappingResult,
    RankingAssessment,
    ScopePack,
    SubmissionScore,
)
from app.workflow import (
    PipelineStage,
    WorkflowRecord,
    advance_workflow,
    create_synthetic_workflow,
)


class AgentExecutor(Protocol):
    async def run(self, agent_name: str, context: dict[str, Any]) -> Any: ...


class WorkflowRepository(Protocol):
    def create(self, record: WorkflowRecord) -> WorkflowRecord: ...
    def save(self, record: WorkflowRecord, *, expected_revision: int) -> WorkflowRecord: ...


class ScopingOrchestrator:
    """Runs one stage at a time and persists after every successful boundary."""

    def __init__(self, repository: WorkflowRepository, executor: AgentExecutor) -> None:
        self.repository = repository
        self.executor = executor

    def _persist(
        self,
        record: WorkflowRecord,
        stage: PipelineStage,
        artifact: dict[str, Any],
    ) -> WorkflowRecord:
        advanced = advance_workflow(record, stage, artifact)
        return self.repository.save(advanced, expected_revision=record.revision)

    async def run(self, submission_id: str, task_description: str) -> WorkflowRecord:
        record = self.repository.create(
            create_synthetic_workflow(submission_id, task_description)
        )

        while True:
            if record.stage in {
                PipelineStage.RANKED,
                PipelineStage.VETOED,
                PipelineStage.REVIEW_REQUIRED,
            }:
                return record

            if record.stage is PipelineStage.RECEIVED:
                intake = IntakeResult.model_validate(
                    await self.executor.run(
                        "intake_agent",
                        {"task_description": record.task_description, "synthetic": True},
                    )
                )
                record = self._persist(
                    record,
                    PipelineStage.INTAKE_COMPLETE,
                    intake.model_dump(mode="json"),
                )
                continue

            if record.stage is PipelineStage.INTAKE_COMPLETE:
                risk = RiskAssessment.model_validate(
                    await self.executor.run(
                        "risk_agent",
                        {"intake": record.artifacts[PipelineStage.INTAKE_COMPLETE.value]},
                    )
                )
                risk_stage = {
                    RiskDecision.CLEAR: PipelineStage.RISK_CLEARED,
                    RiskDecision.REVIEW: PipelineStage.REVIEW_REQUIRED,
                    RiskDecision.VETO: PipelineStage.VETOED,
                }[risk.decision]
                record = self._persist(record, risk_stage, risk.model_dump(mode="json"))
                continue

            if record.stage is PipelineStage.RISK_CLEARED:
                feasibility = FeasibilityResult.model_validate(
                    await self.executor.run(
                        "feasibility_agent",
                        {
                            "intake": record.artifacts[PipelineStage.INTAKE_COMPLETE.value],
                            "risk": record.artifacts[PipelineStage.RISK_CLEARED.value],
                        },
                    )
                )
                record = self._persist(
                    record,
                    PipelineStage.FEASIBILITY_COMPLETE,
                    feasibility.model_dump(mode="json"),
                )
                continue

            if record.stage is PipelineStage.FEASIBILITY_COMPLETE:
                intake = IntakeResult.model_validate(
                    record.artifacts[PipelineStage.INTAKE_COMPLETE.value]
                )
                query = " ".join(
                    [record.task_description, *intake.systems, *intake.repetitive_work]
                )
                candidates = [
                    item.model_dump(mode="json")
                    for item in candidate_capabilities(query)
                ]
                mapping = MappingResult.model_validate(
                    await self.executor.run(
                        "mapping_agent",
                        {
                            "intake": intake.model_dump(mode="json"),
                            "feasibility": record.artifacts[
                                PipelineStage.FEASIBILITY_COMPLETE.value
                            ],
                            "candidate_capabilities": candidates,
                        },
                    )
                )
                validate_mapping(mapping)
                record = self._persist(
                    record,
                    PipelineStage.MAPPING_COMPLETE,
                    mapping.model_dump(mode="json"),
                )
                continue

            if record.stage is PipelineStage.MAPPING_COMPLETE:
                scope = ScopePack.model_validate(
                    await self.executor.run(
                        "scoping_agent",
                        {"validated_artifacts": record.artifacts},
                    )
                )
                record = self._persist(
                    record,
                    PipelineStage.SCOPED,
                    scope.model_dump(mode="json"),
                )
                continue

            if record.stage is PipelineStage.SCOPED:
                assessment = RankingAssessment.model_validate(
                    await self.executor.run(
                        "ranking_agent",
                        {"scope_pack": record.artifacts[PipelineStage.SCOPED.value]},
                    )
                )
                score = SubmissionScore(
                    submission_id=record.submission_id,
                    **assessment.model_dump(),
                )
                artifact = score.model_dump(mode="json")
                artifact["weighted_total"] = score.weighted_total
                record = self._persist(record, PipelineStage.RANKED, artifact)
                continue

            raise RuntimeError(f"Unhandled workflow stage: {record.stage.value}")
