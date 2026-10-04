from typing import Any

import jev
from openai import OpenAI

from invest_games.ports import ReactionJudgement, SpeechJudgement
from invest_games.settings import require_routerai_key, routerai_base_url


@jev.fn(model="jev-1.13")
def _judge_speech(state: dict[str, Any]) -> SpeechJudgement:
    return _judge_speech.state(state)


@jev.fn(model="jev-1.13")
def _judge_reaction(state: dict[str, Any]) -> ReactionJudgement:
    return _judge_reaction.state(state)


class JevBrain:
    def judge_speech(self, state: dict[str, object]) -> SpeechJudgement:
        return _judge_speech(state)

    def judge_reaction(self, state: dict[str, object]) -> ReactionJudgement:
        return _judge_reaction(state)


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


