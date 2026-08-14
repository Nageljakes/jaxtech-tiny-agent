from fastapi.testclient import TestClient

from app.main import app, get_follow_up_worker


class StubWorker:
    def __init__(self) -> None:
        self.calls = 0

    async def run(self) -> dict[str, int]:
        self.calls += 1
        return {"scanned": 2, "reminded": 1, "exhausted": 0}


def test_scheduler_endpoint_runs_model_free_worker(monkeypatch) -> None:
    monkeypatch.setenv("TINY_SCHEDULER_KEY", "scheduler-test-key")
    worker = StubWorker()
    app.dependency_overrides[get_follow_up_worker] = lambda: worker
    try:
        response = TestClient(app).post(
            "/internal/follow-up-reminders",
            headers={"X-Tiny-Scheduler-Key": "scheduler-test-key"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"scanned": 2, "reminded": 1, "exhausted": 0}
    assert worker.calls == 1


def test_scheduler_endpoint_rejects_request_before_worker_initialization(monkeypatch) -> None:
    monkeypatch.setenv("TINY_SCHEDULER_KEY", "scheduler-test-key")
    worker = StubWorker()
    app.dependency_overrides[get_follow_up_worker] = lambda: worker
    try:
        response = TestClient(app).post("/internal/follow-up-reminders")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert worker.calls == 0


def test_scheduler_endpoint_fails_closed_without_configuration(monkeypatch) -> None:
    monkeypatch.delenv("TINY_SCHEDULER_KEY", raising=False)

    response = TestClient(app).post(
        "/internal/follow-up-reminders",
        headers={"X-Tiny-Scheduler-Key": "anything"},
    )

    assert response.status_code == 503
