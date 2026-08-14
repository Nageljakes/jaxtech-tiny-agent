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
