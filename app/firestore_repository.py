"""Firestore persistence with idempotent creation and optimistic revisions."""

from typing import Any

from google.api_core.exceptions import AlreadyExists
from google.cloud.firestore_v1.base_query import FieldFilter

from app.repository import RevisionConflict
from app.workflow import PipelineStage, WorkflowRecord


class FirestoreWorkflowRepository:
    COLLECTION = "submissions"

    def __init__(self, client: Any) -> None:
        self._client = client
        self._collection = client.collection(self.COLLECTION)

    def _document(self, submission_id: str) -> Any:
        return self._collection.document(submission_id)

    def create(self, record: WorkflowRecord) -> WorkflowRecord:
        ref = self._document(record.submission_id)
        payload = record.model_dump(mode="json")
        try:
            ref.create(payload)
            return record
        except AlreadyExists:
            existing = self.load(record.submission_id)
            if existing is None:
                raise RuntimeError("Firestore create conflict without readable record")
            if (
                existing.task_description != record.task_description
                or existing.synthetic != record.synthetic
            ):
                raise ValueError("Submission idempotency conflict")
            return existing

    def load(self, submission_id: str) -> WorkflowRecord | None:
        snapshot = self._document(submission_id).get()
        if not snapshot.exists:
            return None
        return WorkflowRecord.model_validate(snapshot.to_dict())

    def list_by_stage(self, stage: PipelineStage) -> list[WorkflowRecord]:
        query = self._collection.where(
            filter=FieldFilter("stage", "==", stage.value)
        ).where(filter=FieldFilter("synthetic", "==", True))
        return [
            WorkflowRecord.model_validate(snapshot.to_dict())
            for snapshot in query.stream()
        ]

    def save(self, record: WorkflowRecord, *, expected_revision: int) -> WorkflowRecord:
        ref = self._document(record.submission_id)
        transaction = self._client.transaction()
        snapshot = ref.get(transaction=transaction)
        if not snapshot.exists:
            raise KeyError(record.submission_id)
        current = WorkflowRecord.model_validate(snapshot.to_dict())
        if current.revision != expected_revision:
            raise RevisionConflict(
                f"Expected revision {expected_revision}, found {current.revision}"
            )
        saved = record.model_copy(update={"revision": expected_revision + 1})
        transaction.set(ref, saved.model_dump(mode="json"))
        transaction.commit()
        return saved
