"""Persisted follow-up coordination with selective agent re-processing."""

from datetime import UTC, datetime
from typing import Any, Callable, Protocol

from app.follow_up import (
    apply_follow_up_response,
    create_follow_up,
    finalize_rescore,
)
from app.schemas import RankingAssessment, ScopePack, SubmissionScore
from app.workflow import PipelineStage, WorkflowRecord, advance_workflow


class WorkflowRepository(Protocol):
    def load(self, submission_id: str) -> WorkflowRecord | None: ...

    def save(
        self, record: WorkflowRecord, *, expected_revision: int
    ) -> WorkflowRecord: ...


class AgentExecutor(Protocol):
    async def run(self, agent_name: str, context: dict[str, Any]) -> Any: ...


class NotificationSink(Protocol):
    async def publish(self, event: dict[str, Any]) -> None: ...


class FollowUpCoordinator:
    def __init__(
        self,
        repository: WorkflowRepository,
        executor: AgentExecutor,
        notifier: NotificationSink,
        *,
        threshold: float = 8.0,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if not 0 <= threshold <= 10:
            raise ValueError("threshold must be between 0 and 10")
        self.repository = repository
        self.executor = executor
        self.notifier = notifier
        self.threshold = threshold
        self.clock = clock

    def _load(self, submission_id: str) -> WorkflowRecord:
        record = self.repository.load(submission_id)
        if record is None:
            raise ValueError(f"unknown submission: {submission_id}")
        return record

    def request_information(self, submission_id: str) -> WorkflowRecord:
        record = self._load(submission_id)
        waiting = create_follow_up(
            record, last_contact_at=self.clock().isoformat()
        )
        return self.repository.save(waiting, expected_revision=record.revision)

    async def process_response(
        self, submission_id: str, response: str
    ) -> WorkflowRecord:
        waiting = self._load(submission_id)
        received = apply_follow_up_response(waiting, response)
        received = self.repository.save(
            received, expected_revision=waiting.revision
        )

        scope = ScopePack.model_validate(
            await self.executor.run(
                "scoping_agent",
                {
                    "validated_artifacts": received.artifacts,
                    "follow_up_response": received.artifacts[
                        PipelineStage.RESPONSE_RECEIVED.value
                    ],
                    "instruction": "Revise only facts affected by the response.",
                },
            )
        )
        assessment = RankingAssessment.model_validate(
            await self.executor.run(
                "ranking_agent",
                {
                    "scope_pack": scope.model_dump(mode="json"),
                    "instruction": "Re-score using the clarified scope.",
                },
            )
        )
        score = SubmissionScore(
            submission_id=submission_id,
            **assessment.model_dump(),
        )
        finalized = finalize_rescore(
            received,
            weighted_total=score.weighted_total,
            threshold=self.threshold,
            details={
                "scope_pack": scope.model_dump(mode="json"),
                "assessment": assessment.model_dump(mode="json"),
            },
        )
        finalized = self.repository.save(
            finalized, expected_revision=received.revision
        )
        if finalized.stage is PipelineStage.DECISION_READY:
            return await self.deliver_decision_ready(submission_id)
        return finalized

    async def deliver_decision_ready(self, submission_id: str) -> WorkflowRecord:
        record = self._load(submission_id)
        if record.stage is not PipelineStage.DECISION_READY:
            raise ValueError(
                f"expected stage decision_ready, received {record.stage.value}"
            )
        decision = record.artifacts[PipelineStage.DECISION_READY.value]
        event_id = f"decision-ready:{submission_id}:{record.revision}"
        await self.notifier.publish(
            {
                "event_id": event_id,
                "event_type": "submission.decision_ready",
                "submission_id": submission_id,
                "weighted_total": decision["weighted_total"],
            }
        )
        published = advance_workflow(
            record,
            PipelineStage.ESCALATION_PUBLISHED,
            {"event_id": event_id},
        )
        return self.repository.save(
            published, expected_revision=record.revision
        )
