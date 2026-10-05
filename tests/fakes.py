from collections import deque

from invest_games.ports import CompanyDraft, OpeningBelief, ReactionJudgement, SpeechJudgement


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
        openings: list[OpeningBelief] | tuple[OpeningBelief, ...] = (),
    ) -> None:
        self._speeches = deque(speeches)
        self._reactions = deque(reactions)
        self._openings = deque(openings)
        self.speech_states: list[dict[str, object]] = []
        self.reaction_states: list[dict[str, object]] = []
        self.opening_states: list[dict[str, object]] = []

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

    def judge_opening(self, state: dict[str, object]) -> OpeningBelief:
        self.opening_states.append(state)
        if not self._openings:
            raise AssertionError("unexpected opening judgement")
        return self._openings.popleft()


class ScriptedParty:
    def __init__(self, draft: CompanyDraft | dict[str, object]) -> None:
        self._draft = draft if isinstance(draft, CompanyDraft) else CompanyDraft.model_validate(draft)
        self.states: list[dict[str, object]] = []

    def compose(self, state: dict[str, object]) -> CompanyDraft:
        self.states.append(state)
        return self._draft


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

    def judge_opening(self, state: dict[str, object]) -> OpeningBelief:
        raise RuntimeError("routerai down")

    def speak(self, state: dict[str, object]) -> str:
        raise RuntimeError("routerai down")
