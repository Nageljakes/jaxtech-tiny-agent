import asyncio

from app.follow_up_service import FollowUpCoordinator
from app.repository import InMemoryWorkflowRepository
from app.schemas import (
    ArchitectureComponent,
    RankingAssessment,
    ScopePack,
)
from app.workflow import PipelineStage, WorkflowRecord


class SelectiveExecutor:
    def __init__(self, usefulness: int = 9, feasibility: int = 8, interest: int = 7):
        self.calls: list[str] = []
        self.outputs = {
            "scoping_agent": ScopePack(
                problem="Synthetic clarified workflow",
                proposed_workflow=["Receive", "Validate", "Record"],
                architecture=[
                    ArchitectureComponent(
                        name="Tiny",
                        responsibility="Coordinate synthetic work",
                        technology="Google ADK",
                    )
                ],
                integrations=["Synthetic Demo API"],
                estimated_development_hours=16,
                assumptions=["Volume is forty items daily"],
                exclusions=["No production access"],
                open_questions=[],
            ),
            "ranking_agent": RankingAssessment(
                usefulness=usefulness,
                feasibility=feasibility,
                interest=interest,
                justification="Useful, feasible, and judge-visible after clarification.",
            ),
        }

    async def run(self, agent_name: str, context: dict):
        self.calls.append(agent_name)
        return self.outputs[agent_name]


class RecordingNotifier:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def publish(self, event: dict) -> None:
        self.events.append(event)


def seed_ranked(repository: InMemoryWorkflowRepository, submission_id: str) -> None:
    repository.create(
        WorkflowRecord(
            submission_id=submission_id,
            task_description="Synthetic workflow",
            synthetic=True,
            stage=PipelineStage.RANKED,
            revision=6,
            artifacts={
                "intake_complete": {"missing_information": ["Daily volume?"]},
                "risk_cleared": {"decision": "clear"},
                "feasibility_complete": {"classification": "fully_automatable"},
                "mapping_complete": {"matches": []},
                "scoped": {"open_questions": ["Daily volume?"]},
                "ranked": {"weighted_total": 7.4},
            },
        )
    )


def test_coordinator_persists_waiting_state() -> None:
    repository = InMemoryWorkflowRepository()
    seed_ranked(repository, "syn-follow")
    coordinator = FollowUpCoordinator(repository, SelectiveExecutor(), RecordingNotifier())

    result = coordinator.request_information("syn-follow")

    assert result.stage is PipelineStage.WAITING_FOR_INFORMATION
    assert result.revision == 7
    assert repository.load("syn-follow") == result


def test_response_reruns_only_scope_and_ranking_then_escalates() -> None:
    repository = InMemoryWorkflowRepository()
    seed_ranked(repository, "syn-follow")
    executor = SelectiveExecutor()
    notifier = RecordingNotifier()
    coordinator = FollowUpCoordinator(repository, executor, notifier, threshold=8.0)
    coordinator.request_information("syn-follow")

    result = asyncio.run(
        coordinator.process_response("syn-follow", "Forty synthetic items daily")
    )

    assert executor.calls == ["scoping_agent", "ranking_agent"]
    assert result.stage is PipelineStage.NOTIFIED
    assert result.revision == 10
    assert result.artifacts["decision_ready"]["weighted_total"] == 8.2
    assert result.artifacts["decision_ready"]["scope_pack"]["open_questions"] == []
    assert notifier.events == [
        {
            "event_id": "decision-ready:syn-follow:9",
            "event_type": "submission.decision_ready",
            "submission_id": "syn-follow",
            "weighted_total": 8.2,
        }
    ]


def test_below_threshold_rescore_does_not_notify() -> None:
    repository = InMemoryWorkflowRepository()
    seed_ranked(repository, "syn-low")
    executor = SelectiveExecutor(usefulness=5, feasibility=5, interest=5)
    notifier = RecordingNotifier()
    coordinator = FollowUpCoordinator(repository, executor, notifier, threshold=8.0)
    coordinator.request_information("syn-low")

    result = asyncio.run(coordinator.process_response("syn-low", "One item monthly"))

    assert result.stage is PipelineStage.RESCORED
    assert result.artifacts["rescored"]["weighted_total"] == 5.0
    assert notifier.events == []


def test_failed_notification_retries_without_rerunning_agents() -> None:
    class FailingOnceNotifier(RecordingNotifier):
        def __init__(self) -> None:
            super().__init__()
            self.failed = False

        async def publish(self, event: dict) -> None:
            if not self.failed:
                self.failed = True
                raise RuntimeError("synthetic delivery outage")
            await super().publish(event)

    repository = InMemoryWorkflowRepository()
    seed_ranked(repository, "syn-retry")
    executor = SelectiveExecutor()
    notifier = FailingOnceNotifier()
    coordinator = FollowUpCoordinator(repository, executor, notifier, threshold=8.0)
    coordinator.request_information("syn-retry")

    try:
        asyncio.run(coordinator.process_response("syn-retry", "Forty items daily"))
    except RuntimeError as error:
        assert str(error) == "synthetic delivery outage"

    persisted = repository.load("syn-retry")
    assert persisted is not None
    assert persisted.stage is PipelineStage.DECISION_READY
    assert executor.calls == ["scoping_agent", "ranking_agent"]

    result = asyncio.run(coordinator.deliver_decision_ready("syn-retry"))

    assert result.stage is PipelineStage.NOTIFIED
    assert executor.calls == ["scoping_agent", "ranking_agent"]
    assert notifier.events[0]["event_id"] == "decision-ready:syn-retry:9"
