from fastapi.testclient import TestClient

from app.main import app, get_agent_service


class StubAgentService:
    async def prove(self, message: str) -> str:
        assert message == "Prove the Google stack."
        return "Google ADK and Gemini 3.5 are connected."


def test_proof_endpoint_returns_agent_result() -> None:
    app.dependency_overrides[get_agent_service] = lambda: StubAgentService()
    try:
        response = TestClient(app).post(
            "/api/agent/prove", json={"message": "Prove the Google stack."}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Google ADK and Gemini 3.5 are connected.",
        "framework": "google-adk",
        "model": "gemini-3.5-flash-lite",
    }


def test_proof_endpoint_rejects_blank_input() -> None:
    response = TestClient(app).post("/api/agent/prove", json={"message": "   "})

    assert response.status_code == 422
