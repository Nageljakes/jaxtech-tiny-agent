"""Deterministic comparative ranking for challenge submissions."""

from app.schemas import RankedSubmission, SubmissionScore


def rank_submissions(scores: list[SubmissionScore]) -> list[RankedSubmission]:
    """Rank reproducibly: total, dimensions in priority order, then stable ID."""
    ordered = sorted(
        scores,
        key=lambda score: (
            -score.weighted_total,
            -score.usefulness,
            -score.feasibility,
            -score.interest,
            score.submission_id,
        ),
    )
    return [
        RankedSubmission(**score.model_dump(), rank=index)
        for index, score in enumerate(ordered, start=1)
    ]
