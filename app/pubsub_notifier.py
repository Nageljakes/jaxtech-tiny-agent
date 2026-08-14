"""Google Pub/Sub notification adapter for decision-ready events."""

import asyncio
from functools import partial
import json
from typing import Any

from google.cloud import pubsub_v1


class PubSubNotificationSink:
    def __init__(
        self,
        *,
        project_id: str,
        topic_id: str,
        publisher: Any | None = None,
    ) -> None:
        if not project_id or not topic_id:
            raise ValueError("Pub/Sub project and topic are required")
        self.publisher = publisher or pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_id)

    async def publish(self, event: dict[str, Any]) -> None:
        event_id = event.get("event_id")
        event_type = event.get("event_type")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("notification event_id is required")
        if event_type != "submission.decision_ready":
            raise ValueError("unsupported notification event_type")
        payload = json.dumps(
            event,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        future = self.publisher.publish(
            self.topic_path,
            payload,
            event_id=event_id,
            event_type=event_type,
        )
        await asyncio.to_thread(partial(future.result, timeout=30))
