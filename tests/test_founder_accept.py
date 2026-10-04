from invest_games.game import Game
from invest_games.ports import ReactionJudgement, SpeechJudgement
from tests.fakes import NEUTRAL_SPEECH, TALK, ScriptedBrain, ScriptedVoice
from tests.scenarios import scenario


def _game(
    *,
    speeches: list[SpeechJudgement],
    reactions: list[ReactionJudgement] | None = None,
    technique: int = 50,
    morality: int = 70,
) -> tuple[Game, ScriptedBrain]:
    brain = ScriptedBrain(speeches=speeches, reactions=reactions or [])
    game = Game(
        brain=brain,
        voice=ScriptedVoice("За столом."),
        scenario=scenario(technique=technique, morality=morality),
    )
    return game, brain


def test_founder_accepts_by_speech_closes_without_second_jev() -> None:
    game, brain = _game(
        speeches=[
            SpeechJudgement(
                tone=2,
                competence=2,
                believe_facts=False,
                tech_shift=0,
                burn_patience=False,
                founder_accepts=True,
            )
        ],
        reactions=[ReactionJudgement(accept=0, reaction="walk_away")],
    )
    opened = game.start(жадность=50, вежливость=40)
    assert opened.investor_offer is not None

    view = game.submit("согласен, берём ваши цифры")

    assert view.outcome == "раунд"
    assert view.ended is True
    assert brain.reaction_states == []


def test_ordinary_reject_does_not_end_the_deal() -> None:
    game, _brain = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="reject")],
    )
    game.start(жадность=50, вежливость=40)

    view = game.submit("нет, это мало")

    assert view.ended is False
    assert view.outcome is None


def test_founder_purchase_lines_place_the_same_offer() -> None:
    first, _ = _game(speeches=[NEUTRAL_SPEECH], reactions=[TALK])
    first.start(жадность=40, вежливость=40)
    a = first.submit("предложить покупка 500_000")

    second, _ = _game(speeches=[NEUTRAL_SPEECH], reactions=[TALK])
    second.start(жадность=40, вежливость=40)
    b = second.submit("предложить купить 500 000€")

    assert a.founder_offer == b.founder_offer
    assert a.founder_offer is not None
    assert a.founder_offer.kind == "покупка"
    assert a.founder_offer.amount == 500_000


def test_investor_accepts_founder_purchase_only_below_valuation() -> None:
    cheap, _ = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=4, reaction="talk")],
    )
    cheap.start(жадность=40, вежливость=40)
    taken = cheap.submit("предложить покупка 900000")
    assert taken.outcome == "покупка"

    dear, _ = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=4, reaction="talk")],
    )
    dear.start(жадность=40, вежливость=40)
    refused = dear.submit("предложить покупка 1000000")
    assert refused.outcome != "покупка"
    assert refused.ended is False
