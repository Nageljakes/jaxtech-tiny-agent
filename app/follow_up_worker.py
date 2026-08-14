"""Model-free worker for bounded stale follow-up reminders."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Protocol

from app.workflow import PipelineStage, WorkflowRecord


class WorkflowRepository(Protocol):
    def list_by_stage(self, stage: PipelineStage) -> list[WorkflowRecord]: ...

    def save(
        self, record: WorkflowRecord, *, expected_revision: int
    ) -> WorkflowRecord: ...


class NotificationSink(Protocol):
    async def publish(self, event: dict[str, Any]) -> None: ...


class FollowUpReminderWorker:
    def __init__(
        self,
        repository: WorkflowRepository,
        notifier: NotificationSink,
        *,
        cooldown: timedelta = timedelta(hours=24),
        max_attempts: int = 3,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if cooldown <= timedelta(0):
            raise ValueError("cooldown must be positive")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        self.repository = repository
        self.notifier = notifier
        self.cooldown = cooldown
        self.max_attempts = max_attempts
        self.clock = clock

    async def run(self) -> dict[str, int]:
        now = self.clock()
        records = self.repository.list_by_stage(
            PipelineStage.WAITING_FOR_INFORMATION
        )
        reminded = 0
        exhausted = 0
        for record in records:
            waiting = record.artifacts.get(
                PipelineStage.WAITING_FOR_INFORMATION.value, {}
            )
            attempt = waiting.get("attempt")
            contacted_raw = waiting.get("last_contact_at")
            if not isinstance(attempt, int) or not isinstance(contacted_raw, str):
                continue
            if attempt >= self.max_attempts:
                exhausted += 1
                continue
            try:
                contacted_at = datetime.fromisoformat(contacted_raw)
            except ValueError:
                continue
            if contacted_at.tzinfo is None or now - contacted_at < self.cooldown:
                continue

            next_attempt = attempt + 1
            event = {
                "event_id": (
                    f"follow-up-reminder:{record.submission_id}:{next_attempt}"
                ),
                "event_type": "submission.follow_up_reminder",
                "submission_id": record.submission_id,
                "attempt": next_attempt,
                "questions": waiting.get("questions", []),
            }
            await self.notifier.publish(event)

            artifacts = deepcopy(record.artifacts)
            artifacts[PipelineStage.WAITING_FOR_INFORMATION.value].update(
                {
                    "attempt": next_attempt,
                    "last_contact_at": now.isoformat(),
                }
            )
            updated = record.model_copy(update={"artifacts": artifacts})
            self.repository.save(
                updated, expected_revision=record.revision
            )
            reminded += 1
        return {
            "scanned": len(records),
            "reminded": reminded,
            "exhausted": exhausted,
        }
