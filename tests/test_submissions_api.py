from fastapi.testclient import TestClient

from app.main import app, get_scoping_orchestrator
from app.workflow import PipelineStage, WorkflowRecord


class StubOrchestrator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def run(self, submission_id: str, task_description: str) -> WorkflowRecord:
        self.calls.append((submission_id, task_description))
        return WorkflowRecord(
            submission_id=submission_id,
            task_description=task_description,
            synthetic=True,
            stage=PipelineStage.RANKED,
            revision=6,
            artifacts={"ranked": {"weighted_total": 8.2}},
        )


def test_synthetic_submission_endpoint_returns_persisted_workflow(monkeypatch) -> None:
    monkeypatch.setenv("TINY_DEMO_KEY", "synthetic-test-key")
    orchestrator = StubOrchestrator()
    app.dependency_overrides[get_scoping_orchestrator] = lambda: orchestrator
    try:
        response = TestClient(app).post(
            "/api/submissions",
            headers={"X-Tiny-Demo-Key": "synthetic-test-key"},
            json={
                "submission_id": "syn-demo-001",
                "task_description": "Copy synthetic form rows into a demo tracker",
                "synthetic": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["stage"] == "ranked"
    assert response.json()["artifacts"]["ranked"]["weighted_total"] == 8.2
    assert orchestrator.calls == [
        ("syn-demo-001", "Copy synthetic form rows into a demo tracker")
    ]


def test_submission_endpoint_rejects_non_synthetic_input_before_orchestration(monkeypatch) -> None:
    monkeypatch.setenv("TINY_DEMO_KEY", "synthetic-test-key")
    orchestrator = StubOrchestrator()
    app.dependency_overrides[get_scoping_orchestrator] = lambda: orchestrator
    try:
        response = TestClient(app).post(
            "/api/submissions",
            headers={"X-Tiny-Demo-Key": "synthetic-test-key"},
            json={
                "submission_id": "real-001",
                "task_description": "Do not process this",
                "synthetic": False,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert orchestrator.calls == []


def test_submission_id_must_use_synthetic_namespace(monkeypatch) -> None:
    monkeypatch.setenv("TINY_DEMO_KEY", "synthetic-test-key")
    response = TestClient(app).post(
        "/api/submissions",
        headers={"X-Tiny-Demo-Key": "synthetic-test-key"},
        json={
            "submission_id": "entrant-001",
            "task_description": "Synthetic words are not enough",
            "synthetic": True,
        },
    )

    assert response.status_code == 422


def test_submission_endpoint_rejects_missing_demo_key(monkeypatch) -> None:
    monkeypatch.setenv("TINY_DEMO_KEY", "synthetic-test-key")

    response = TestClient(app).post(
        "/api/submissions",
        json={
            "submission_id": "syn-demo-001",
            "task_description": "Synthetic task",
            "synthetic": True,
        },
    )

    assert response.status_code == 401


def test_submission_endpoint_fails_closed_when_secret_is_unconfigured(monkeypatch) -> None:
    monkeypatch.delenv("TINY_DEMO_KEY", raising=False)

    response = TestClient(app).post(
        "/api/submissions",
        headers={"X-Tiny-Demo-Key": "anything"},
        json={
            "submission_id": "syn-demo-001",
            "task_description": "Synthetic task",
            "synthetic": True,
        },
    )

    assert response.status_code == 503
