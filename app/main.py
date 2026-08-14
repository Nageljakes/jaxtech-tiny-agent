"""Cloud Run HTTP entrypoint for the Jaxtech Tiny stack proof."""

from functools import lru_cache
import os
import secrets
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.cloud import firestore
from pydantic import BaseModel, Field

from app.adk_executor import StructuredAdkExecutor
from app.agent import MODEL
from app.firestore_repository import FirestoreWorkflowRepository
from app.follow_up_service import FollowUpCoordinator
from app.follow_up_worker import FollowUpReminderWorker
from app.orchestrator import ScopingOrchestrator
from app.pubsub_notifier import PubSubNotificationSink
from app.service import AgentService
from app.workflow import WorkflowRecord

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
    allow_headers=["Content-Type", "X-Tiny-Demo-Key"],
)


@app.middleware("http")
async def protect_billable_submission_endpoint(request, call_next):
    """Reject unauthorized workflow runs before Firestore or Gemini initialization."""
    if (
        request.method != "OPTIONS"
        and request.url.path.startswith("/api/submissions")
    ):
        configured_key = os.getenv("TINY_DEMO_KEY")
        if not configured_key:
            return JSONResponse(
                status_code=503,
                content={"detail": "Synthetic demo endpoint is not configured"},
            )
        supplied_key = request.headers.get("X-Tiny-Demo-Key", "")
        if not secrets.compare_digest(supplied_key, configured_key):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    if request.url.path == "/internal/follow-up-reminders":
        configured_key = os.getenv("TINY_SCHEDULER_KEY")
        if not configured_key:
            return JSONResponse(
                status_code=503,
                content={"detail": "Scheduler endpoint is not configured"},
            )
        supplied_key = request.headers.get("X-Tiny-Scheduler-Key", "")
        if not secrets.compare_digest(supplied_key, configured_key):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)

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


class SubmissionRequest(BaseModel):
    submission_id: str = Field(pattern=r"^syn-[a-zA-Z0-9-]{1,80}$")
    task_description: str = Field(min_length=1, max_length=50_000, pattern=r".*\S.*")
    synthetic: Literal[True]


class FollowUpResponseRequest(BaseModel):
    response: str = Field(min_length=1, max_length=20_000, pattern=r".*\S.*")
    synthetic: Literal[True]


def get_agent_service() -> AgentService:
    return _agent_service


@lru_cache(maxsize=1)
def get_workflow_repository() -> FirestoreWorkflowRepository:
    return FirestoreWorkflowRepository(firestore.Client())


@lru_cache(maxsize=1)
def get_scoping_orchestrator() -> ScopingOrchestrator:
    """Construct production dependencies lazily so validation fails before cloud I/O."""
    return ScopingOrchestrator(get_workflow_repository(), StructuredAdkExecutor())


@lru_cache(maxsize=1)
def get_notification_sink() -> PubSubNotificationSink:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    topic_id = os.getenv("TINY_DECISION_TOPIC", "tiny-decision-ready")
    return PubSubNotificationSink(project_id=project_id, topic_id=topic_id)


@lru_cache(maxsize=1)
def get_follow_up_coordinator() -> FollowUpCoordinator:
    return FollowUpCoordinator(
        get_workflow_repository(), StructuredAdkExecutor(), get_notification_sink()
    )


@lru_cache(maxsize=1)
def get_follow_up_worker() -> FollowUpReminderWorker:
    return FollowUpReminderWorker(
        get_workflow_repository(), get_notification_sink()
    )


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


@app.post("/api/submissions", response_model=WorkflowRecord)
async def process_synthetic_submission(
    request: SubmissionRequest,
    orchestrator: Annotated[ScopingOrchestrator, Depends(get_scoping_orchestrator)],
) -> WorkflowRecord:
    """Run the complete fixture-gated autonomous scoping workflow."""
    return await orchestrator.run(request.submission_id, request.task_description)


@app.get("/api/submissions/{submission_id}", response_model=WorkflowRecord)
def get_synthetic_submission(
    submission_id: str,
    repository: Annotated[
        FirestoreWorkflowRepository, Depends(get_workflow_repository)
    ],
) -> WorkflowRecord:
    record = repository.load(submission_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Synthetic submission not found")
    return record


@app.post(
    "/api/submissions/{submission_id}/follow-up",
    response_model=WorkflowRecord,
)
def request_synthetic_follow_up(
    submission_id: str,
    coordinator: Annotated[
        FollowUpCoordinator, Depends(get_follow_up_coordinator)
    ],
) -> WorkflowRecord:
    return coordinator.request_information(submission_id)


@app.post(
    "/api/submissions/{submission_id}/responses",
    response_model=WorkflowRecord,
)
async def process_synthetic_follow_up_response(
    submission_id: str,
    request: FollowUpResponseRequest,
    coordinator: Annotated[
        FollowUpCoordinator, Depends(get_follow_up_coordinator)
    ],
) -> WorkflowRecord:
    return await coordinator.process_response(submission_id, request.response)


@app.post("/internal/follow-up-reminders")
async def run_follow_up_reminders(
    worker: Annotated[
        FollowUpReminderWorker, Depends(get_follow_up_worker)
    ],
) -> dict[str, int]:
    """Cloud Scheduler target; performs no model inference."""
    return await worker.run()
