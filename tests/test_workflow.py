import pytest

from app.repository import InMemoryWorkflowRepository, RevisionConflict
from app.workflow import (
    PipelineStage,
    WorkflowRecord,
    advance_workflow,
    create_synthetic_workflow,
)


def test_synthetic_workflow_creation_is_idempotent() -> None:
    repository = InMemoryWorkflowRepository()

    first = repository.create(
        create_synthetic_workflow("syn-001", "Copy demo form rows into a tracker")
    )
    replay = repository.create(
        create_synthetic_workflow("syn-001", "Copy demo form rows into a tracker")
    )

    assert replay == first
    assert repository.count == 1


def test_repository_rejects_same_id_with_different_payload() -> None:
    repository = InMemoryWorkflowRepository()
    repository.create(create_synthetic_workflow("syn-001", "First synthetic task"))

    with pytest.raises(ValueError, match="idempotency conflict"):
        repository.create(create_synthetic_workflow("syn-001", "Changed synthetic task"))


def test_pipeline_advances_only_in_declared_order() -> None:
    record = create_synthetic_workflow("syn-001", "Synthetic workflow")

    with pytest.raises(ValueError, match="expected intake_complete"):
        advance_workflow(record, PipelineStage.FEASIBILITY_COMPLETE, {"level": "partial"})


def test_risk_veto_is_terminal() -> None:
    record = create_synthetic_workflow("syn-001", "Synthetic workflow")
    record = advance_workflow(record, PipelineStage.INTAKE_COMPLETE, {"trigger": "demo"})
    record = advance_workflow(record, PipelineStage.VETOED, {"reason": "physical safety"})

    assert record.stage is PipelineStage.VETOED
    with pytest.raises(ValueError, match="terminal"):
        advance_workflow(record, PipelineStage.FEASIBILITY_COMPLETE, {"level": "partial"})


def test_complete_synthetic_pipeline_is_persisted_with_revision_checks() -> None:
    repository = InMemoryWorkflowRepository()
    record = repository.create(create_synthetic_workflow("syn-001", "Synthetic workflow"))
    stages = [
        PipelineStage.INTAKE_COMPLETE,
        PipelineStage.RISK_CLEARED,
        PipelineStage.FEASIBILITY_COMPLETE,
        PipelineStage.MAPPING_COMPLETE,
        PipelineStage.SCOPED,
        PipelineStage.RANKED,
    ]

    for stage in stages:
        updated = advance_workflow(record, stage, {"stage": stage.value})
        record = repository.save(updated, expected_revision=record.revision)

    assert record.stage is PipelineStage.RANKED
    assert record.revision == 6
    assert set(record.artifacts) == {stage.value for stage in stages}

    stale = record.model_copy(update={"revision": 1})
    with pytest.raises(RevisionConflict):
        repository.save(stale, expected_revision=1)


def test_real_submission_is_rejected_while_fixture_gate_is_enabled() -> None:
    with pytest.raises(ValueError, match="synthetic-only"):
        WorkflowRecord(
            submission_id="real-001",
            task_description="Do not process this record",
            synthetic=False,
        )
