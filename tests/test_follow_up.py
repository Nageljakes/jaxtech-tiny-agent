import pytest

from app.follow_up import (
    apply_follow_up_response,
    create_follow_up,
    finalize_rescore,
)
from app.workflow import PipelineStage, WorkflowRecord


def ranked_record(open_questions: list[str]) -> WorkflowRecord:
    return WorkflowRecord(
        submission_id="syn-follow-up",
        task_description="Synthetic workflow",
        synthetic=True,
        stage=PipelineStage.RANKED,
        revision=6,
        artifacts={
            "scoped": {"open_questions": open_questions},
            "ranked": {"weighted_total": 7.4},
        },
    )


def test_ranked_submission_with_questions_enters_waiting_state() -> None:
    result = create_follow_up(ranked_record(["How many items arrive each day?"]))

    assert result.stage is PipelineStage.WAITING_FOR_INFORMATION
    assert result.artifacts["waiting_for_information"] == {
        "questions": ["How many items arrive each day?"],
        "attempt": 1,
    }


def test_follow_up_requires_ranked_submission_and_real_questions() -> None:
    with pytest.raises(ValueError, match="no open questions"):
        create_follow_up(ranked_record([]))

    waiting = create_follow_up(ranked_record(["Which demo system?"]))
    with pytest.raises(ValueError, match="expected stage ranked"):
        create_follow_up(waiting)


def test_nonempty_synthetic_response_is_persisted_for_rescoring() -> None:
    waiting = create_follow_up(ranked_record(["Daily volume?"]))

    result = apply_follow_up_response(waiting, "About 40 synthetic items per day.")

    assert result.stage is PipelineStage.RESPONSE_RECEIVED
    assert result.artifacts["response_received"]["response"] == (
        "About 40 synthetic items per day."
    )


def test_empty_response_is_rejected() -> None:
    waiting = create_follow_up(ranked_record(["Daily volume?"]))

    with pytest.raises(ValueError, match="non-empty"):
        apply_follow_up_response(waiting, "   ")


def test_rescore_crossing_threshold_becomes_decision_ready() -> None:
    response = apply_follow_up_response(
        create_follow_up(ranked_record(["Daily volume?"])),
        "About 40 synthetic items per day.",
    )

    result = finalize_rescore(response, weighted_total=8.1, threshold=8.0)

    assert result.stage is PipelineStage.DECISION_READY
    assert result.artifacts["decision_ready"] == {
        "weighted_total": 8.1,
        "threshold": 8.0,
        "escalate": True,
    }


def test_rescore_below_threshold_is_persisted_without_escalation() -> None:
    response = apply_follow_up_response(
        create_follow_up(ranked_record(["Daily volume?"])),
        "Only one synthetic item per month.",
    )

    result = finalize_rescore(response, weighted_total=5.2, threshold=8.0)

    assert result.stage is PipelineStage.RESCORED
    assert result.artifacts["rescored"]["escalate"] is False


def test_scores_and_thresholds_are_bounded() -> None:
    response = apply_follow_up_response(
        create_follow_up(ranked_record(["Daily volume?"])),
        "Synthetic answer",
    )

    with pytest.raises(ValueError, match="between 0 and 10"):
        finalize_rescore(response, weighted_total=10.1, threshold=8.0)
