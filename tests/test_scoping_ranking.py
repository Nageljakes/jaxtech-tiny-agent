from app.agent import MODEL
from app.pipeline import ranking_agent, scoping_agent
from app.ranking import rank_submissions
from app.schemas import (
    ArchitectureComponent,
    RankingAssessment,
    ScopePack,
    SubmissionScore,
)


def synthetic_scope_pack() -> ScopePack:
    return ScopePack(
        problem="Synthetic form submissions are copied into a tracker by hand.",
        proposed_workflow=[
            "Receive a synthetic form event",
            "Validate required fields",
            "Create a row in the demo tracker",
        ],
        architecture=[
            ArchitectureComponent(
                name="Intake API",
                responsibility="Accept and validate synthetic submissions",
                technology="Cloud Run",
            )
        ],
        integrations=["Synthetic form webhook", "Google Sheets API"],
        estimated_development_hours=14,
        assumptions=["The synthetic form schema remains stable"],
        exclusions=["No production personal data", "No payment processing"],
        open_questions=["What is the expected daily submission volume?"],
    )


def test_scope_pack_contains_complete_decision_material() -> None:
    pack = synthetic_scope_pack()

    assert pack.estimated_development_hours == 14
    assert pack.architecture[0].technology == "Cloud Run"
    assert "No payment processing" in pack.exclusions


def test_weighted_ranking_total_is_deterministic() -> None:
    score = SubmissionScore(
        submission_id="syn-001",
        usefulness=9,
        feasibility=8,
        interest=7,
        justification="Strong synthetic operational workflow.",
    )

    assert score.weighted_total == 8.2


def test_rank_submissions_uses_total_then_usefulness_tie_break() -> None:
    lower_usefulness = SubmissionScore(
        submission_id="syn-b",
        usefulness=7,
        feasibility=9,
        interest=8,
        justification="Synthetic candidate B.",
    )
    higher_usefulness = SubmissionScore(
        submission_id="syn-a",
        usefulness=8,
        feasibility=8,
        interest=8,
        justification="Synthetic candidate A.",
    )

    ranked = rank_submissions([lower_usefulness, higher_usefulness])

    assert [item.submission_id for item in ranked] == ["syn-a", "syn-b"]
    assert [item.rank for item in ranked] == [1, 2]


def test_ranking_is_stable_for_exact_ties() -> None:
    scores = [
        SubmissionScore(
            submission_id=submission_id,
            usefulness=8,
            feasibility=8,
            interest=8,
            justification="Synthetic exact tie.",
        )
        for submission_id in ["syn-z", "syn-a"]
    ]

    assert [item.submission_id for item in rank_submissions(scores)] == [
        "syn-a",
        "syn-z",
    ]


def test_scoping_and_ranking_agents_use_structured_google_outputs() -> None:
    assert scoping_agent.model == MODEL == "gemini-3.5-flash-lite"
    assert scoping_agent.output_schema is ScopePack
    assert scoping_agent.output_key == "scope_pack"
    assert ranking_agent.model == MODEL
    assert ranking_agent.output_schema is RankingAssessment
    assert ranking_agent.output_key == "ranking_assessment"
