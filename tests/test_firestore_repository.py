import pytest

from app.firestore_repository import FirestoreWorkflowRepository
from app.repository import RevisionConflict
from app.workflow import PipelineStage, advance_workflow, create_synthetic_workflow


class FakeSnapshot:
    def __init__(self, data: dict | None) -> None:
        self.exists = data is not None
        self._data = data

    def to_dict(self) -> dict | None:
        return self._data


class FakeDocument:
    def __init__(self, store: dict[str, dict], key: str) -> None:
        self.store = store
        self.key = key

    def create(self, data: dict) -> None:
        if self.key in self.store:
            from google.api_core.exceptions import AlreadyExists

            raise AlreadyExists("exists")
        self.store[self.key] = data

    def get(self, transaction=None) -> FakeSnapshot:
        return FakeSnapshot(self.store.get(self.key))


class FakeCollection:
    def __init__(self, store: dict[str, dict]) -> None:
        self.store = store

    def document(self, key: str) -> FakeDocument:
        return FakeDocument(self.store, key)


class FakeTransaction:
    def __init__(self, store: dict[str, dict]) -> None:
        self.store = store
        self.pending: tuple[FakeDocument, dict] | None = None

    def set(self, ref: FakeDocument, data: dict) -> None:
        self.pending = (ref, data)

    def commit(self) -> None:
        assert self.pending is not None
        ref, data = self.pending
        ref.store[ref.key] = data


class FakeFirestoreClient:
    def __init__(self) -> None:
        self.store: dict[str, dict] = {}
        self.collection_name: str | None = None

    def collection(self, name: str) -> FakeCollection:
        self.collection_name = name
        return FakeCollection(self.store)

    def transaction(self) -> FakeTransaction:
        return FakeTransaction(self.store)


def test_firestore_repository_round_trips_workflow_state() -> None:
    client = FakeFirestoreClient()
    repository = FirestoreWorkflowRepository(client)
    record = repository.create(create_synthetic_workflow("syn-001", "Synthetic task"))
    record = advance_workflow(record, PipelineStage.INTAKE_COMPLETE, {"trigger": "demo"})
    saved = repository.save(record, expected_revision=0)

    assert client.collection_name == "submissions"
    assert saved.revision == 1
    assert repository.load("syn-001") == saved
    assert client.store["syn-001"]["stage"] == "intake_complete"


def test_firestore_create_is_idempotent_but_rejects_changed_payload() -> None:
    repository = FirestoreWorkflowRepository(FakeFirestoreClient())
    first = repository.create(create_synthetic_workflow("syn-001", "Synthetic task"))

    assert repository.create(first) == first
    with pytest.raises(ValueError, match="idempotency conflict"):
        repository.create(create_synthetic_workflow("syn-001", "Changed task"))


def test_firestore_repository_rejects_stale_revision() -> None:
    repository = FirestoreWorkflowRepository(FakeFirestoreClient())
    record = repository.create(create_synthetic_workflow("syn-001", "Synthetic task"))

    with pytest.raises(RevisionConflict):
        repository.save(record, expected_revision=2)
