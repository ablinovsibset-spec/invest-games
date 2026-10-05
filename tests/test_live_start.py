from invest_games.game import ApiError, Game, InputError
from invest_games.ports import OpeningBelief
from invest_games.scenario import Scenario

from tests.fakes import ScriptedBrain, ScriptedVoice


LIVE_COMPANY = {
    "компания": "Aurora",
    "питч": "Ночной диспетчер для малых складов без обещаний чудес.",
    "запрос": 1_000_000,
}


def _live_game(
    *,
    morality: int = 70,
    technique: int = 55,
    brain: ScriptedBrain | None = None,
    voice: ScriptedVoice | None = None,
) -> tuple[Game, ScriptedBrain, ScriptedVoice]:
    brain = brain or ScriptedBrain(
        openings=[OpeningBelief(technique=technique, morality=morality)],
    )
    voice = voice or ScriptedVoice("Живой стол открыт.")
    game = Game(brain=brain, voice=voice)
    return game, brain, voice


def test_live_start_shows_company_composed_by_founder() -> None:
    game, brain, voice = _live_game()

    view = game.start(жадность=40, вежливость=60, **LIVE_COMPANY)

    assert brain.opening_states == [
        {"company_name": "Aurora", "pitch": LIVE_COMPANY["питч"]}
    ]
    assert set(brain.opening_states[0]) == {"company_name", "pitch"}
    assert view.company_name == "Aurora"
    assert view.pitch == LIVE_COMPANY["питч"]
    assert view.ask == 1_000_000
    assert view.remarks[-1].text == "Живой стол открыт."
    budget = voice.states[0]["budget"]
    assert isinstance(budget, int)
    assert 200_000 <= budget <= 500_000
    assert voice.states[0]["valuation"] == 1_000_000
    assert voice.states[0]["investor_offer"] is not None


def test_live_start_low_morality_opens_without_round() -> None:
    game, _brain, voice = _live_game(morality=20)

    view = game.start(жадность=50, вежливость=40, **LIVE_COMPANY)

    assert view.investor_offer is None
    assert voice.states[0]["investor_offer"] is None


def test_live_start_normal_morality_opens_formula_round() -> None:
    game, _brain, voice = _live_game(morality=70)

    view = game.start(жадность=50, вежливость=40, **LIVE_COMPANY)

    assert view.investor_offer is not None
    assert view.investor_offer.kind == "раунд"
    assert view.investor_offer.share == 20
    budget = voice.states[0]["budget"]
    assert isinstance(budget, int)
    assert view.investor_offer.amount == min(budget, 150_000)


def test_fixture_start_does_not_call_opening_jev() -> None:
    brain = ScriptedBrain(openings=[OpeningBelief(technique=10, morality=10)])
    game = Game(
        brain=brain,
        voice=ScriptedVoice("Шаблон."),
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

    assert brain.opening_states == []
    assert view.company_name == "Nimbus"
    assert view.ask == 1_000_000


def test_empty_pitch_does_not_leave_a_table() -> None:
    brain = ScriptedBrain(openings=[OpeningBelief(technique=55, morality=70)])
    game = Game(brain=brain, voice=ScriptedVoice("не должны"))

    try:
        game.start(
            жадность=40,
            вежливость=60,
            компания="Aurora",
            питч="   ",
            запрос=1_000_000,
        )
    except InputError:
        pass
    else:
        raise AssertionError("empty pitch was accepted")

    assert brain.opening_states == []
    try:
        game.view()
    except InputError:
        return
    raise AssertionError("broken live start left a table")


def test_empty_name_does_not_leave_a_table() -> None:
    brain = ScriptedBrain(openings=[OpeningBelief(technique=55, morality=70)])
    game = Game(brain=brain, voice=ScriptedVoice("не должны"))

    try:
        game.start(
            жадность=40,
            вежливость=60,
            компания="  ",
            питч="Ночной диспетчер.",
            запрос=1_000_000,
        )
    except InputError:
        pass
    else:
        raise AssertionError("empty name was accepted")

    assert brain.opening_states == []
    try:
        game.view()
    except InputError:
        return
    raise AssertionError("broken live start left a table")


def test_ask_out_of_range_does_not_leave_a_table() -> None:
    game = Game(
        brain=ScriptedBrain(openings=[OpeningBelief(technique=55, morality=70)]),
        voice=ScriptedVoice("нет"),
    )

    try:
        game.start(
            жадность=40,
            вежливость=60,
            компания="Aurora",
            питч="Нормальный питч.",
            запрос=100,
        )
    except InputError:
        pass
    else:
        raise AssertionError("out-of-range ask was accepted")

    try:
        game.view()
    except InputError:
        return
    raise AssertionError("broken live start left a table")


def test_opening_jev_failure_does_not_leave_a_table() -> None:
    class BoomOpening(ScriptedBrain):
        def judge_opening(self, state: dict[str, object]) -> OpeningBelief:
            raise RuntimeError("opening down")

    game = Game(
        brain=BoomOpening(),
        voice=ScriptedVoice("нет"),
    )

    try:
        game.start(жадность=40, вежливость=60, **LIVE_COMPANY)
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
    game, _brain, _voice = _live_game()
    game.start(жадность=20, вежливость=20, **LIVE_COMPANY)

    left = game.submit("уйти")

    assert left.outcome == "отказ основателя"
    assert left.ended is True


def test_live_view_hides_private_fields() -> None:
    game, _brain, _voice = _live_game()
    view = game.start(жадность=30, вежливость=20, **LIVE_COMPANY)
    names = set(view.__dataclass_fields__)

    assert "valuation" not in names
    assert "technique" not in names
    assert "morality" not in names
    assert "budget" not in names
