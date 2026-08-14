from fastapi.testclient import TestClient

from app.main import app


def test_github_pages_origin_is_allowed() -> None:
    response = TestClient(app).options(
        "/api/agent/prove",
        headers={
            "Origin": "https://nageljakes.github.io",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://nageljakes.github.io"
