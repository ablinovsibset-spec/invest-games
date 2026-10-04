from collections import deque

from invest_games.ports import ReactionJudgement, SpeechJudgement


NEUTRAL_SPEECH = SpeechJudgement(
    tone=2,
    competence=2,
    believe_facts=False,
    tech_shift=0,
    burn_patience=False,
    founder_accepts=False,
)

TALK = ReactionJudgement(accept=0, reaction="talk")


class ScriptedBrain:
    def __init__(
        self,
        *,
        speeches: list[SpeechJudgement] | tuple[SpeechJudgement, ...] = (),
        reactions: list[ReactionJudgement] | tuple[ReactionJudgement, ...] = (),
    ) -> None:
        self._speeches = deque(speeches)
        self._reactions = deque(reactions)
        self.speech_states: list[dict[str, object]] = []
        self.reaction_states: list[dict[str, object]] = []

    def judge_speech(self, state: dict[str, object]) -> SpeechJudgement:
        self.speech_states.append(state)
        if not self._speeches:
            raise AssertionError("unexpected speech judgement")
        return self._speeches.popleft()

    def judge_reaction(self, state: dict[str, object]) -> ReactionJudgement:
        self.reaction_states.append(state)
        if not self._reactions:
            raise AssertionError("unexpected reaction judgement")
        return self._reactions.popleft()


class ScriptedVoice:
    def __init__(self, lines: str | list[str] = "Реплика инвестора.") -> None:
        self._lines = deque([lines] if isinstance(lines, str) else lines)
        self.states: list[dict[str, object]] = []

    def speak(self, state: dict[str, object]) -> str:
        self.states.append(state)
        if not self._lines:
            return "Реплика инвестора."
        line = self._lines.popleft()
        if not self._lines:
            self._lines.append(line)
        return line


class BoomPort:
    def judge_speech(self, state: dict[str, object]) -> SpeechJudgement:
        raise RuntimeError("routerai down")

    def judge_reaction(self, state: dict[str, object]) -> ReactionJudgement:
        raise RuntimeError("routerai down")

    def speak(self, state: dict[str, object]) -> str:
        raise RuntimeError("routerai down")
