from typing import Literal, Protocol

from pydantic import BaseModel, Field


class SpeechJudgement(BaseModel):
    tone: int = Field(ge=0, le=4, description="How polite versus pushy the founder is this turn")
    competence: int = Field(
        ge=0,
        le=4,
        description="How skillfully the founder argues and trades this turn",
    )
    believe_facts: bool = Field(description="Whether the investor believes the founder's factual claims")
    tech_shift: int = Field(
        ge=0,
        le=3,
        description="How much those believed facts raise technique: none, slight, clear, strong",
    )
    founder_accepts: bool = Field(
        description="Whether the founder is accepting the investor offer already on the table"
    )


class ReactionJudgement(BaseModel):
    accept: int = Field(
        ge=0,
        le=4,
        description="How likely the investor is to accept the founder's offer",
        json_schema_extra={
            "levels": [
                "Definitely reject",
                "Probably reject",
                "Uncertain",
                "Probably accept",
                "Definitely accept",
            ]
        },
    )
    reaction: Literal["accept", "counter", "reject", "walk_away", "purchase", "talk"] = Field(
        description="How the investor should react among the legal actions"
    )


class OpeningBelief(BaseModel):
    technique: int = Field(
        ge=0,
        le=100,
        description=(
            "Honest starting technique from pitch and name only. "
            "Use the full 0–100 range; do not squeeze into a comfortable mid band"
        ),
    )
    morality: int = Field(
        ge=0,
        le=100,
        description=(
            "Honest starting morality from pitch and name only. "
            "A dark pitch may be low; do not raise it for playability"
        ),
    )


class Brain(Protocol):
    def judge_speech(self, state: dict[str, object]) -> SpeechJudgement: ...

    def judge_reaction(self, state: dict[str, object]) -> ReactionJudgement: ...

    def judge_opening(self, state: dict[str, object]) -> OpeningBelief: ...


class Voice(Protocol):
    def speak(self, state: dict[str, object]) -> str: ...
