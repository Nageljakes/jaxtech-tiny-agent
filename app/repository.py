"""Persistence interfaces for workflow records."""

from copy import deepcopy

from app.workflow import WorkflowRecord
from app.workflow import PipelineStage


class RevisionConflict(RuntimeError):
    """Raised when a stale worker attempts to overwrite newer workflow state."""


class InMemoryWorkflowRepository:
    """Deterministic test repository implementing production persistence semantics."""

    def __init__(self) -> None:
        self._records: dict[str, WorkflowRecord] = {}

    @property
    def count(self) -> int:
        return len(self._records)

    def create(self, record: WorkflowRecord) -> WorkflowRecord:
        existing = self._records.get(record.submission_id)
        if existing is not None:
            if (
                existing.task_description != record.task_description
                or existing.synthetic != record.synthetic
            ):
                raise ValueError("Submission idempotency conflict")
            return deepcopy(existing)
        self._records[record.submission_id] = deepcopy(record)
        return deepcopy(record)

    def load(self, submission_id: str) -> WorkflowRecord | None:
        record = self._records.get(submission_id)
        return deepcopy(record) if record else None

    def list_by_stage(self, stage: PipelineStage) -> list[WorkflowRecord]:
        return [
            deepcopy(record)
            for record in self._records.values()
            if record.stage is stage and record.synthetic
        ]

    def save(self, record: WorkflowRecord, *, expected_revision: int) -> WorkflowRecord:
        existing = self._records.get(record.submission_id)
        if existing is None:
            raise KeyError(record.submission_id)
        if existing.revision != expected_revision:
            raise RevisionConflict(
                f"Expected revision {expected_revision}, found {existing.revision}"
            )
        saved = record.model_copy(update={"revision": expected_revision + 1})
        self._records[record.submission_id] = deepcopy(saved)
        return deepcopy(saved)
