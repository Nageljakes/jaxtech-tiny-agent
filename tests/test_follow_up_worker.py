import asyncio
from datetime import UTC, datetime, timedelta

from app.follow_up_worker import FollowUpReminderWorker
from app.repository import InMemoryWorkflowRepository
from app.workflow import PipelineStage, WorkflowRecord


NOW = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)


class RecordingNotifier:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def publish(self, event: dict) -> None:
        self.events.append(event)


def waiting_record(
    submission_id: str,
    *,
    age_hours: int,
    attempt: int = 1,
    synthetic: bool = True,
) -> WorkflowRecord:
    requested = NOW - timedelta(hours=age_hours)
    return WorkflowRecord(
        submission_id=submission_id,
        task_description="Synthetic workflow",
        synthetic=synthetic,
        stage=PipelineStage.WAITING_FOR_INFORMATION,
        revision=7,
        artifacts={
            "waiting_for_information": {
                "questions": ["Daily volume?"],
                "attempt": attempt,
                "last_contact_at": requested.isoformat(),
            }
        },
    )


def test_worker_reminds_only_due_synthetic_records_without_model_calls() -> None:
    repository = InMemoryWorkflowRepository()
    due = repository.create(waiting_record("syn-due", age_hours=25))
    repository.create(waiting_record("syn-fresh", age_hours=2))
    notifier = RecordingNotifier()
    worker = FollowUpReminderWorker(
        repository,
        notifier,
        cooldown=timedelta(hours=24),
        max_attempts=3,
        clock=lambda: NOW,
    )

    result = asyncio.run(worker.run())

    assert result == {"scanned": 2, "reminded": 1, "exhausted": 0}
    assert notifier.events == [
        {
            "event_id": "follow-up-reminder:syn-due:2",
            "event_type": "submission.follow_up_reminder",
            "submission_id": "syn-due",
            "attempt": 2,
            "questions": ["Daily volume?"],
        }
    ]
    saved = repository.load(due.submission_id)
    assert saved is not None
    assert saved.revision == 8
    assert saved.artifacts["waiting_for_information"]["attempt"] == 2
    assert saved.artifacts["waiting_for_information"]["last_contact_at"] == NOW.isoformat()


def test_worker_respects_attempt_limit_and_reports_exhausted() -> None:
    repository = InMemoryWorkflowRepository()
    repository.create(waiting_record("syn-exhausted", age_hours=48, attempt=3))
    notifier = RecordingNotifier()
    worker = FollowUpReminderWorker(
        repository,
        notifier,
        cooldown=timedelta(hours=24),
        max_attempts=3,
        clock=lambda: NOW,
    )

    result = asyncio.run(worker.run())

    assert result == {"scanned": 1, "reminded": 0, "exhausted": 1}
    assert notifier.events == []


def test_worker_is_silent_when_nothing_is_due() -> None:
    repository = InMemoryWorkflowRepository()
    repository.create(waiting_record("syn-fresh", age_hours=1))
    notifier = RecordingNotifier()
    worker = FollowUpReminderWorker(repository, notifier, clock=lambda: NOW)

    result = asyncio.run(worker.run())

    assert result == {"scanned": 1, "reminded": 0, "exhausted": 0}
    assert notifier.events == []
