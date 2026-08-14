import pytest

from app.domain import (
    RiskAssessment,
    RiskDecision,
    RiskFlag,
    Submission,
    SubmissionStatus,
    apply_risk_assessment,
)


def synthetic_submission() -> Submission:
    return Submission(
        id="syn-001",
        task_description="Copy new website enquiries into a demo spreadsheet.",
        synthetic=True,
    )


def test_submission_defaults_to_received_without_contact_data() -> None:
    submission = synthetic_submission()

    assert submission.status is SubmissionStatus.RECEIVED
    assert submission.synthetic is True
    assert submission.submitter is None


def test_risk_veto_stops_unsafe_submission() -> None:
    submission = synthetic_submission()
    assessment = RiskAssessment(
        decision=RiskDecision.VETO,
        flags=[RiskFlag.PHYSICAL_SAFETY],
        reasons=["Synthetic scenario would directly control safety-critical machinery."],
    )

    updated = apply_risk_assessment(submission, assessment)

    assert updated.status is SubmissionStatus.VETOED
    assert updated.risk is assessment
    assert updated.may_continue is False


def test_clear_risk_assessment_allows_pipeline_to_continue() -> None:
    submission = synthetic_submission()
    assessment = RiskAssessment(
        decision=RiskDecision.CLEAR,
        flags=[],
        reasons=["Synthetic low-risk administrative workflow."],
    )

    updated = apply_risk_assessment(submission, assessment)

    assert updated.status is SubmissionStatus.RISK_CLEARED
    assert updated.may_continue is True


def test_non_synthetic_submission_is_rejected_in_fixture_mode() -> None:
    submission = synthetic_submission().model_copy(update={"synthetic": False})
    assessment = RiskAssessment(
        decision=RiskDecision.CLEAR,
        flags=[],
        reasons=["Not relevant; fixture gate must stop first."],
    )

    with pytest.raises(ValueError, match="synthetic-only"):
        apply_risk_assessment(submission, assessment, synthetic_only=True)
