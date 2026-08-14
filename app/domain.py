"""Typed submission lifecycle and fail-closed risk gate."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SubmissionStatus(StrEnum):
    RECEIVED = "received"
    RISK_CLEARED = "risk_cleared"
    NEEDS_REVIEW = "needs_review"
    VETOED = "vetoed"


class RiskDecision(StrEnum):
    CLEAR = "clear"
    REVIEW = "review"
    VETO = "veto"


class RiskFlag(StrEnum):
    PERSONAL_DATA = "personal_data"
    VENDOR_TERMS = "vendor_terms"
    MONEY = "money"
    PHYSICAL_SAFETY = "physical_safety"
    ILLEGALITY = "illegality"
    CYBER_SECURITY = "cyber_security"


class Submitter(BaseModel):
    """Optional contact data; excluded from model-facing workflow state."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: str | None = None
    phone: str | None = None


class RiskAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: RiskDecision
    flags: list[RiskFlag]
    reasons: list[str] = Field(min_length=1)


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    task_description: str = Field(min_length=1, max_length=50_000)
    synthetic: bool
    status: SubmissionStatus = SubmissionStatus.RECEIVED
    submitter: Submitter | None = None
    risk: RiskAssessment | None = None

    @property
    def may_continue(self) -> bool:
        return self.status is SubmissionStatus.RISK_CLEARED


def apply_risk_assessment(
    submission: Submission,
    assessment: RiskAssessment,
    *,
    synthetic_only: bool = True,
) -> Submission:
    """Apply the binding risk decision; fixture mode rejects real records."""
    if synthetic_only and not submission.synthetic:
        raise ValueError("Phase 2 fixture mode is synthetic-only")

    next_status = {
        RiskDecision.CLEAR: SubmissionStatus.RISK_CLEARED,
        RiskDecision.REVIEW: SubmissionStatus.NEEDS_REVIEW,
        RiskDecision.VETO: SubmissionStatus.VETOED,
    }[assessment.decision]
    return submission.model_copy(
        update={"risk": assessment, "status": next_status},
    )
