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


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=50_000, pattern=r".*\S.*")
    opener: bool = False
    history: list[dict[str, str]] = Field(default_factory=list, max_length=8)


class ChatResponse(BaseModel):
    reply: str
    source: str = Field(serialization_alias="from")


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


@app.post("/api/chat", response_model=ChatResponse, response_model_by_alias=True)
async def chat(
    request: ChatRequest,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> ChatResponse:
    """Compatibility endpoint used while the challenge UI migrates to Google."""
    reply = await service.prove(request.message)
    return ChatResponse(reply=reply, source="google-adk")
