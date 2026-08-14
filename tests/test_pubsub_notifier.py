import asyncio
import json

from app.pubsub_notifier import PubSubNotificationSink


class FakeFuture:
    def __init__(self) -> None:
        self.result_calls = 0

    def result(self, timeout: int):
        self.result_calls += 1
        assert timeout == 30
        return "message-123"


class FakePublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes, dict[str, str]]] = []
        self.future = FakeFuture()

    def topic_path(self, project: str, topic: str) -> str:
        return f"projects/{project}/topics/{topic}"

    def publish(self, topic_path: str, data: bytes, **attributes):
        self.calls.append((topic_path, data, attributes))
        return self.future


def test_pubsub_sink_publishes_canonical_event_and_waits_for_ack() -> None:
    publisher = FakePublisher()
    sink = PubSubNotificationSink(
        project_id="synthetic-project",
        topic_id="tiny-decision-ready",
        publisher=publisher,
    )
    event = {
        "event_id": "decision-ready:syn-001:9",
        "event_type": "submission.decision_ready",
        "submission_id": "syn-001",
        "weighted_total": 8.2,
    }

    asyncio.run(sink.publish(event))

    topic, payload, attributes = publisher.calls[0]
    assert topic == "projects/synthetic-project/topics/tiny-decision-ready"
    assert json.loads(payload) == event
    assert attributes == {
        "event_id": "decision-ready:syn-001:9",
        "event_type": "submission.decision_ready",
    }
    assert publisher.future.result_calls == 1
