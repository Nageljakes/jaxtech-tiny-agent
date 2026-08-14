from fastapi.testclient import TestClient

from app.main import app, get_agent_service


class StubChatService:
    async def prove(self, message: str) -> str:
        assert message == "Automate my synthetic home"
        return "Which devices and systems should the assistant coordinate?"


def test_chat_compatibility_endpoint_returns_reply() -> None:
    app.dependency_overrides[get_agent_service] = lambda: StubChatService()
    try:
        response = TestClient(app).post(
            "/api/chat",
            json={
                "message": "Automate my synthetic home",
                "opener": True,
                "history": [],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Which devices and systems should the assistant coordinate?",
        "from": "google-adk",
    }
