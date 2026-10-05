from invest_games.game import ApiError, Game, InputError
from invest_games.ports import OpeningBelief
from invest_games.scenario import Scenario

from tests.fakes import ScriptedBrain, ScriptedParty, ScriptedVoice


LIVE_DRAFT = {
    "company_name": "Aurora",
    "pitch": "Ночной диспетчер для малых складов без обещаний чудес.",
    "ask": 1_000_000,
}


def _live_game(
    *,
    morality: int = 70,
    technique: int = 55,
    draft: dict[str, object] | None = None,
    party: ScriptedParty | None = None,
    brain: ScriptedBrain | None = None,
    voice: ScriptedVoice | None = None,
) -> tuple[Game, ScriptedParty, ScriptedBrain, ScriptedVoice]:
    party = party or ScriptedParty(draft or LIVE_DRAFT)
    brain = brain or ScriptedBrain(
        openings=[OpeningBelief(technique=technique, morality=morality)],
    )
    voice = voice or ScriptedVoice("Живой стол открыт.")
    game = Game(brain=brain, voice=voice, party=party)
    return game, party, brain, voice


def test_live_start_shows_company_composed_by_party() -> None:
    game, party, brain, voice = _live_game()

    view = game.start(жадность=40, вежливость=60)

    assert party.states == [{"greed": 40, "politeness": 60}]
    assert brain.opening_states == [
        {"company_name": "Aurora", "pitch": LIVE_DRAFT["pitch"]}
    ]
    assert set(brain.opening_states[0]) == {"company_name", "pitch"}
    assert view.company_name == "Aurora"
    assert view.pitch == LIVE_DRAFT["pitch"]
    assert view.ask == 1_000_000
    assert view.remarks[-1].text == "Живой стол открыт."
    budget = voice.states[0]["budget"]
    assert isinstance(budget, int)
    assert 200_000 <= budget <= 500_000
    assert voice.states[0]["valuation"] == 1_000_000
    assert voice.states[0]["investor_offer"] is not None


def test_live_start_low_morality_opens_without_round() -> None:
    game, _party, _brain, voice = _live_game(morality=20)

    view = game.start(жадность=50, вежливость=40)

    assert view.investor_offer is None
    assert voice.states[0]["investor_offer"] is None


def test_live_start_normal_morality_opens_formula_round() -> None:
    game, _party, _brain, voice = _live_game(morality=70)

    view = game.start(жадность=50, вежливость=40)

    assert view.investor_offer is not None
    assert view.investor_offer.kind == "раунд"
    assert view.investor_offer.share == 20
    budget = voice.states[0]["budget"]
    assert isinstance(budget, int)
    assert view.investor_offer.amount == min(budget, 150_000)


def test_fixture_start_does_not_call_party_or_opening_jev() -> None:
    party = ScriptedParty(LIVE_DRAFT)
    brain = ScriptedBrain(openings=[OpeningBelief(technique=10, morality=10)])
    game = Game(
        brain=brain,
        voice=ScriptedVoice("Шаблон."),
        party=party,
        scenario=Scenario(
            company_name="Nimbus",
            pitch="Складской помощник.",
            ask=1_000_000,
            budget=800_000,
            technique=50,
            morality=70,
        ),
    )

    view = game.start(жадность=40, вежливость=60)

    assert party.states == []
    assert brain.opening_states == []
    assert view.company_name == "Nimbus"
    assert view.ask == 1_000_000


def test_empty_pitch_does_not_leave_a_table_and_does_not_retry() -> None:
    party = ScriptedParty(
        {
            "company_name": "Aurora",
            "pitch": "   ",
            "ask": 1_000_000,
        }
    )
    brain = ScriptedBrain(openings=[OpeningBelief(technique=55, morality=70)])
    game = Game(brain=brain, voice=ScriptedVoice("не должны"), party=party)

    try:
        game.start(жадность=40, вежливость=60)
    except ApiError:
        pass
    else:
        raise AssertionError("empty pitch was accepted")

    assert len(party.states) == 1
    assert brain.opening_states == []
    try:
        game.view()
    except InputError:
        return
    raise AssertionError("broken live start left a table")


def test_empty_name_does_not_leave_a_table_and_does_not_retry() -> None:
    party = ScriptedParty(
        {
            "company_name": "  ",
            "pitch": "Ночной диспетчер.",
            "ask": 1_000_000,
        }
    )
    brain = ScriptedBrain(openings=[OpeningBelief(technique=55, morality=70)])
    game = Game(brain=brain, voice=ScriptedVoice("не должны"), party=party)

    try:
        game.start(жадность=40, вежливость=60)
    except ApiError:
        pass
    else:
        raise AssertionError("empty name was accepted")

    assert len(party.states) == 1
    assert brain.opening_states == []
    try:
        game.view()
    except InputError:
        return
    raise AssertionError("broken live start left a table")


def test_ask_out_of_range_does_not_leave_a_table() -> None:
    party = ScriptedParty(
        {
            "company_name": "Aurora",
            "pitch": "Нормальный питч.",
            "ask": 100,
        }
    )
    game = Game(
        brain=ScriptedBrain(openings=[OpeningBelief(technique=55, morality=70)]),
        voice=ScriptedVoice("нет"),
        party=party,
    )

    try:
        game.start(жадность=40, вежливость=60)
    except ApiError:
        pass
    else:
        raise AssertionError("out-of-range ask was accepted")

    try:
        game.view()
    except InputError:
        return
    raise AssertionError("broken live start left a table")


def test_party_failure_does_not_leave_a_table() -> None:
    class BoomParty:
        def compose(self, state: dict[str, object]):
            raise RuntimeError("party down")

    game = Game(
        brain=ScriptedBrain(openings=[OpeningBelief(technique=55, morality=70)]),
        voice=ScriptedVoice("нет"),
        party=BoomParty(),
    )

    try:
        game.start(жадность=40, вежливость=60)
    except ApiError:
        pass
    else:
        raise AssertionError("party failure was swallowed")

    try:
        game.view()
    except InputError:
        return
    raise AssertionError("party failure left a table")


def test_opening_jev_failure_does_not_leave_a_table() -> None:
    class BoomOpening(ScriptedBrain):
        def judge_opening(self, state: dict[str, object]) -> OpeningBelief:
            raise RuntimeError("opening down")

    game = Game(
        brain=BoomOpening(),
        voice=ScriptedVoice("нет"),
        party=ScriptedParty(LIVE_DRAFT),
    )

    try:
        game.start(жадность=40, вежливость=60)
    except ApiError:
        pass
    else:
        raise AssertionError("opening failure was swallowed")

    try:
        game.view()
    except InputError:
        return
    raise AssertionError("opening failure left a table")


def test_live_founder_refusal_still_closes() -> None:
    game, _party, _brain, _voice = _live_game()
    game.start(жадность=20, вежливость=20)

    left = game.submit("уйти")

    assert left.outcome == "отказ основателя"
    assert left.ended is True


def test_live_view_hides_private_fields() -> None:
    game, _party, _brain, _voice = _live_game()
    view = game.start(жадность=30, вежливость=20)
    names = set(view.__dataclass_fields__)

    assert "valuation" not in names
    assert "technique" not in names
    assert "morality" not in names
    assert "budget" not in names
