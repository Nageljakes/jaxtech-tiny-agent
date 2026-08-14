"""Cloud Run HTTP entrypoint for the Jaxtech Tiny stack proof."""

from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agent import MODEL
from app.service import AgentService

app = FastAPI(title="Jaxtech Tiny", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nageljakes.github.io",
        "https://jaxtech.co.za",
        "https://www.jaxtech.co.za",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

_agent_service = AgentService()


class ProofRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2_000, pattern=r".*\S.*")


class ProofResponse(BaseModel):
    reply: str
    framework: str
    model: str


def get_agent_service() -> AgentService:
    return _agent_service


@app.get("/health")
def health() -> dict[str, str | int]:
    """Return non-secret deployment and stack identity."""
    return {
        "status": "ok",
        "framework": "google-adk",
        "model": MODEL,
        "phase": 1,
    }


@app.post("/api/agent/prove", response_model=ProofResponse)
async def prove_stack(
    request: ProofRequest,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> ProofResponse:
    reply = await service.prove(request.message)
    return ProofResponse(reply=reply, framework="google-adk", model=MODEL)
