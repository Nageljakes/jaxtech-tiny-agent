from fastapi.testclient import TestClient

from app.main import app


def test_health_exposes_phase_one_stack_proof() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "framework": "google-adk",
        "model": "gemini-3.5-flash-lite",
        "phase": 1,
    }
