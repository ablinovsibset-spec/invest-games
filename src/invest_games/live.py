from typing import Any

import jev
from openai import OpenAI
from pydantic import BaseModel, Field

from invest_games.ports import OpeningBelief, ReactionJudgement, SpeechJudgement
from invest_games.settings import require_routerai_key, routerai_base_url


class _OpeningBeliefScore(BaseModel):
    """Jev score form of opening belief.

    int ge/le becomes one Score level per integer; RouterAI allows at most 10.
    float ge/le interpolates across a few labels, then we round back to 0–100.
    """

    technique: float = Field(
        ge=0,
        le=100,
        description=(
            "Honest starting technique from pitch and name only. "
            "Use the full 0–100 range; do not squeeze into a comfortable mid band"
        ),
        json_schema_extra={
            "levels": ["0", "25", "50", "75", "100"],
        },
    )
    morality: float = Field(
        ge=0,
        le=100,
        description=(
            "Honest starting morality from pitch and name only. "
            "A dark pitch may be low; do not raise it for playability"
        ),
        json_schema_extra={
            "levels": ["0", "25", "50", "75", "100"],
        },
    )


@jev.fn(model="jev-1.13")
def _judge_speech(state: dict[str, Any]) -> SpeechJudgement:
    return _judge_speech.state(state)


@jev.fn(model="jev-1.13")
def _judge_reaction(state: dict[str, Any]) -> ReactionJudgement:
    return _judge_reaction.state(state)


@jev.fn(model="jev-1.13")
def _judge_opening(state: dict[str, Any]) -> _OpeningBeliefScore:
    """Honest starting technique and morality from pitch and name only.

    Use the full 0–100 range. Do not squeeze belief into a comfortable mid band
    for playability. A dark pitch may score low morality; a hype pitch may score
    high technique.
    """
    return _judge_opening.state(state)


class JevBrain:
    def judge_speech(self, state: dict[str, object]) -> SpeechJudgement:
        return _judge_speech(state)

    def judge_reaction(self, state: dict[str, object]) -> ReactionJudgement:
        return _judge_reaction(state)

    def judge_opening(self, state: dict[str, object]) -> OpeningBelief:
        belief = _judge_opening(state)
        technique = int(round(belief.technique))
        morality = int(round(belief.morality))
        if not 0 <= technique <= 100 or not 0 <= morality <= 100:
            raise RuntimeError("стартовый Jev вернул веру вне 0–100")
        return OpeningBelief(technique=technique, morality=morality)


class LlmVoice:
    def __init__(self) -> None:
        base = routerai_base_url()
        self._client = OpenAI(api_key=require_routerai_key(), base_url=f"{base}/v1")

    def speak(self, state: dict[str, object]) -> str:
        decision = state.get("reaction") or state.get("opening")
        response = self._client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты голос Инвестора за столом. Решение уже принято. "
                        "Напиши только реплику по уже выбранной реакции и цифрам. "
                        "Не меняй исход и не придумывай новые суммы."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Решение: {decision}. Состояние: {state}",
                },
            ],
        )
        text = response.choices[0].message.content
        if not text or not text.strip():
            raise RuntimeError("пустой голос RouterAI")
        return text.strip()
