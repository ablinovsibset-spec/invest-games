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
    burn_patience: bool = Field(description="Whether this turn should burn one unit of patience")
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


class Brain(Protocol):
    def judge_speech(self, state: dict[str, object]) -> SpeechJudgement: ...

    def judge_reaction(self, state: dict[str, object]) -> ReactionJudgement: ...


class Voice(Protocol):
    def speak(self, state: dict[str, object]) -> str: ...
