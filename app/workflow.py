"""Auditable synthetic workflow lifecycle with a binding risk veto."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PipelineStage(StrEnum):
    RECEIVED = "received"
    INTAKE_COMPLETE = "intake_complete"
    RISK_CLEARED = "risk_cleared"
    REVIEW_REQUIRED = "review_required"
    VETOED = "vetoed"
    FEASIBILITY_COMPLETE = "feasibility_complete"
    MAPPING_COMPLETE = "mapping_complete"
    SCOPED = "scoped"
    RANKED = "ranked"
    WAITING_FOR_INFORMATION = "waiting_for_information"
    RESPONSE_RECEIVED = "response_received"
    RESCORED = "rescored"
    DECISION_READY = "decision_ready"
    ESCALATION_PUBLISHED = "escalation_published"


_ALLOWED_NEXT: dict[PipelineStage, tuple[PipelineStage, ...]] = {
    PipelineStage.RECEIVED: (PipelineStage.INTAKE_COMPLETE,),
    PipelineStage.INTAKE_COMPLETE: (
        PipelineStage.RISK_CLEARED,
        PipelineStage.REVIEW_REQUIRED,
        PipelineStage.VETOED,
    ),
    PipelineStage.RISK_CLEARED: (PipelineStage.FEASIBILITY_COMPLETE,),
    PipelineStage.FEASIBILITY_COMPLETE: (PipelineStage.MAPPING_COMPLETE,),
    PipelineStage.MAPPING_COMPLETE: (PipelineStage.SCOPED,),
    PipelineStage.SCOPED: (PipelineStage.RANKED,),
    PipelineStage.RANKED: (PipelineStage.WAITING_FOR_INFORMATION,),
    PipelineStage.WAITING_FOR_INFORMATION: (PipelineStage.RESPONSE_RECEIVED,),
    PipelineStage.RESPONSE_RECEIVED: (
        PipelineStage.RESCORED,
        PipelineStage.DECISION_READY,
    ),
    PipelineStage.RESCORED: (),
    PipelineStage.DECISION_READY: (PipelineStage.ESCALATION_PUBLISHED,),
    PipelineStage.ESCALATION_PUBLISHED: (),
    PipelineStage.REVIEW_REQUIRED: (),
    PipelineStage.VETOED: (),
}


class WorkflowRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_id: str = Field(min_length=1)
    task_description: str = Field(min_length=1, max_length=50_000)
    synthetic: bool = True
    stage: PipelineStage = PipelineStage.RECEIVED
    revision: int = Field(default=0, ge=0)
    artifacts: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def enforce_fixture_gate(self) -> "WorkflowRecord":
        if not self.synthetic:
            raise ValueError("Phase 2 workflow is synthetic-only")
        return self


def create_synthetic_workflow(submission_id: str, task_description: str) -> WorkflowRecord:
    return WorkflowRecord(
        submission_id=submission_id,
        task_description=task_description,
        synthetic=True,
    )


def advance_workflow(
    record: WorkflowRecord,
    next_stage: PipelineStage,
    artifact: dict[str, Any],
) -> WorkflowRecord:
    allowed = _ALLOWED_NEXT[record.stage]
    if not allowed:
        raise ValueError(f"Stage {record.stage.value} is terminal")
    if next_stage not in allowed:
        expected = " or ".join(stage.value for stage in allowed)
        raise ValueError(
            f"Invalid transition from {record.stage.value}; expected {expected}"
        )
    artifacts = {**record.artifacts, next_stage.value: artifact}
    return record.model_copy(update={"stage": next_stage, "artifacts": artifacts})
