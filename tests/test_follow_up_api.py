from fastapi.testclient import TestClient

from app.main import (
    app,
    get_follow_up_coordinator,
    get_workflow_repository,
)
from app.workflow import PipelineStage, WorkflowRecord


class StubRepository:
    def __init__(self, record: WorkflowRecord | None) -> None:
        self.record = record

    def load(self, submission_id: str) -> WorkflowRecord | None:
        if self.record and self.record.submission_id == submission_id:
            return self.record
        return None


class StubCoordinator:
    def __init__(self, record: WorkflowRecord) -> None:
        self.record = record
        self.follow_up_calls: list[str] = []
        self.response_calls: list[tuple[str, str]] = []

    def request_information(self, submission_id: str) -> WorkflowRecord:
        self.follow_up_calls.append(submission_id)
        return self.record.model_copy(
            update={"stage": PipelineStage.WAITING_FOR_INFORMATION}
        )

    async def process_response(
        self, submission_id: str, response: str
    ) -> WorkflowRecord:
        self.response_calls.append((submission_id, response))
        return self.record.model_copy(update={"stage": PipelineStage.NOTIFIED})


def fixture_record() -> WorkflowRecord:
    return WorkflowRecord(
        submission_id="syn-audit-001",
        task_description="Synthetic workflow",
        synthetic=True,
        stage=PipelineStage.RANKED,
        revision=6,
        artifacts={"ranked": {"weighted_total": 7.4}},
    )


def authorized_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("TINY_DEMO_KEY", "synthetic-test-key")
    return TestClient(app)


def test_get_submission_returns_complete_audit_record(monkeypatch) -> None:
    record = fixture_record()
    app.dependency_overrides[get_workflow_repository] = lambda: StubRepository(record)
    try:
        response = authorized_client(monkeypatch).get(
            "/api/submissions/syn-audit-001",
            headers={"X-Tiny-Demo-Key": "synthetic-test-key"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["revision"] == 6
    assert response.json()["artifacts"]["ranked"]["weighted_total"] == 7.4


def test_get_unknown_submission_returns_404(monkeypatch) -> None:
    app.dependency_overrides[get_workflow_repository] = lambda: StubRepository(None)
    try:
        response = authorized_client(monkeypatch).get(
            "/api/submissions/syn-missing",
            headers={"X-Tiny-Demo-Key": "synthetic-test-key"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_follow_up_and_response_routes_delegate_to_coordinator(monkeypatch) -> None:
    coordinator = StubCoordinator(fixture_record())
    app.dependency_overrides[get_follow_up_coordinator] = lambda: coordinator
    client = authorized_client(monkeypatch)
    headers = {"X-Tiny-Demo-Key": "synthetic-test-key"}
    try:
        follow_up = client.post(
            "/api/submissions/syn-audit-001/follow-up", headers=headers
        )
        response = client.post(
            "/api/submissions/syn-audit-001/responses",
            headers=headers,
            json={"response": "Forty synthetic items daily", "synthetic": True},
        )
    finally:
        app.dependency_overrides.clear()

    assert follow_up.status_code == 200
    assert follow_up.json()["stage"] == "waiting_for_information"
    assert response.status_code == 200
    assert response.json()["stage"] == "notified"
    assert coordinator.follow_up_calls == ["syn-audit-001"]
    assert coordinator.response_calls == [
        ("syn-audit-001", "Forty synthetic items daily")
    ]


def test_nested_submission_routes_are_protected_before_dependencies(monkeypatch) -> None:
    monkeypatch.setenv("TINY_DEMO_KEY", "synthetic-test-key")

    response = TestClient(app).get("/api/submissions/syn-audit-001")

    assert response.status_code == 401


def test_submission_preflight_allows_demo_key_header_without_secret_value() -> None:
    response = TestClient(app).options(
        "/api/submissions/syn-audit-001/responses",
        headers={
            "Origin": "https://nageljakes.github.io",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Tiny-Demo-Key, Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "https://nageljakes.github.io"
    )
    assert "x-tiny-demo-key" in response.headers[
        "access-control-allow-headers"
    ].lower()
