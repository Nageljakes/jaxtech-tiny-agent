"""Deterministic asynchronous follow-up and escalation transitions."""

from app.workflow import PipelineStage, WorkflowRecord, advance_workflow


def create_follow_up(record: WorkflowRecord) -> WorkflowRecord:
    if record.stage is not PipelineStage.RANKED:
        raise ValueError(
            f"expected stage ranked, received {record.stage.value}"
        )
    scope = record.artifacts.get(PipelineStage.SCOPED.value, {})
    questions = scope.get("open_questions", [])
    if not questions:
        raise ValueError("scope pack has no open questions")
    return advance_workflow(
        record,
        PipelineStage.WAITING_FOR_INFORMATION,
        {"questions": questions, "attempt": 1},
    )


def apply_follow_up_response(
    record: WorkflowRecord, response: str
) -> WorkflowRecord:
    if record.stage is not PipelineStage.WAITING_FOR_INFORMATION:
        raise ValueError(
            "expected stage waiting_for_information, "
            f"received {record.stage.value}"
        )
    cleaned = response.strip()
    if not cleaned:
        raise ValueError("follow-up response must be non-empty")
    return advance_workflow(
        record,
        PipelineStage.RESPONSE_RECEIVED,
        {"response": cleaned, "synthetic": True},
    )


def finalize_rescore(
    record: WorkflowRecord,
    *,
    weighted_total: float,
    threshold: float,
    details: dict | None = None,
) -> WorkflowRecord:
    if record.stage is not PipelineStage.RESPONSE_RECEIVED:
        raise ValueError(
            f"expected stage response_received, received {record.stage.value}"
        )
    if not 0 <= weighted_total <= 10 or not 0 <= threshold <= 10:
        raise ValueError("weighted total and threshold must be between 0 and 10")
    escalate = weighted_total >= threshold
    target = (
        PipelineStage.DECISION_READY if escalate else PipelineStage.RESCORED
    )
    artifact = dict(details or {})
    artifact.update(
        {
            "weighted_total": weighted_total,
            "threshold": threshold,
            "escalate": escalate,
        }
    )
    return advance_workflow(
        record,
        target,
        artifact,
    )
