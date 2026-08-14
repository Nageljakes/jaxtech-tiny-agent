"""Structured outputs shared by the autonomous scoping agents."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class IntakeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repetitive_work: list[str] = Field(min_length=1)
    systems: list[str] = Field(min_length=1)
    trigger: str = Field(min_length=1)
    desired_outcome: str = Field(min_length=1)
    missing_information: list[str]
    language: str = Field(description="BCP-47 language tag, such as en-ZA or zu-ZA")

    @property
    def is_complete(self) -> bool:
        return not self.missing_information


class AutomationLevel(StrEnum):
    FULL = "fully_automatable"
    PARTIAL = "partially_automatable"
    NOT_SAFE = "not_safely_automatable"


class FeasibilityResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: AutomationLevel
    rationale: str = Field(min_length=1)
    assumptions: list[str] = Field(min_length=1)
    exclusions: list[str]
    estimated_development_hours: int = Field(ge=1, le=2_000)


class CapabilityMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str = Field(min_length=1)
    integrations: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class MappingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matches: list[CapabilityMatch]
    unmapped_requirements: list[str]


class ArchitectureComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    responsibility: str = Field(min_length=1)
    technology: str = Field(min_length=1)


class ScopePack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem: str = Field(min_length=1)
    proposed_workflow: list[str] = Field(min_length=1)
    architecture: list[ArchitectureComponent] = Field(min_length=1)
    integrations: list[str]
    estimated_development_hours: int = Field(ge=1, le=2_000)
    assumptions: list[str] = Field(min_length=1)
    exclusions: list[str]
    open_questions: list[str]


class RankingAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usefulness: int = Field(ge=0, le=10)
    feasibility: int = Field(ge=0, le=10)
    interest: int = Field(ge=0, le=10)
    justification: str = Field(min_length=1)


class SubmissionScore(RankingAssessment):
    submission_id: str = Field(min_length=1)

    @property
    def weighted_total(self) -> float:
        # Utility and feasibility dominate; novelty cannot rescue an impractical task.
        return (self.usefulness * 4 + self.feasibility * 4 + self.interest * 2) / 10


class RankedSubmission(SubmissionScore):
    rank: int = Field(ge=1)
