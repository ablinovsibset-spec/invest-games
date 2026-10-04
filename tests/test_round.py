from invest_games.game import Game, InputError
from invest_games.ports import ReactionJudgement, SpeechJudgement
from tests.fakes import NEUTRAL_SPEECH, TALK, ScriptedBrain, ScriptedVoice
from tests.scenarios import scenario


def _game(
    *,
    speeches: list[SpeechJudgement],
    reactions: list[ReactionJudgement],
    technique: int = 50,
    morality: int = 70,
    budget: int = 800_000,
) -> Game:
    return Game(
        brain=ScriptedBrain(speeches=speeches, reactions=reactions),
        voice=ScriptedVoice("За столом."),
        scenario=scenario(technique=technique, morality=morality, budget=budget),
    )


def test_amount_formats_place_the_same_round() -> None:
    first = _game(speeches=[NEUTRAL_SPEECH], reactions=[TALK])
    first.start(жадность=50, вежливость=40)
    a = first.submit("предложить 500_000 20")

    second = _game(speeches=[NEUTRAL_SPEECH], reactions=[TALK])
    second.start(жадность=50, вежливость=40)
    b = second.submit("предложить 500 000€ 20")

    assert a.founder_offer == b.founder_offer
    assert a.founder_offer is not None
    assert a.founder_offer.kind == "раунд"
    assert a.founder_offer.amount == 500_000
    assert a.founder_offer.share == 20


def test_bad_share_or_bare_offer_is_input_error_and_table_stays() -> None:
    game = _game(speeches=[], reactions=[])
    opened = game.start(жадность=50, вежливость=40)
    remarks = opened.remarks

    try:
        game.submit("предложить 500000 0")
    except InputError:
        pass
    else:
        raise AssertionError("share 0 must be an input error")
    assert game.view().remarks == remarks
    assert game.view().patience == opened.patience

    try:
        game.submit("предложить просто так")
    except InputError:
        pass
    else:
        raise AssertionError("bare предложить must be an input error")
    assert game.view().remarks == remarks


def test_prose_does_not_create_a_round() -> None:
    game = _game(speeches=[NEUTRAL_SPEECH], reactions=[TALK])
    game.start(жадность=50, вежливость=40)

    view = game.submit("ну давай тысяч пятьсот")

    assert view.founder_offer is None


def test_legal_accept_closes_as_round() -> None:
    game = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=3, reaction="talk")],
    )
    game.start(жадность=50, вежливость=40)

    view = game.submit("предложить 100000 20")

    assert view.outcome == "раунд"
    assert view.ended is True


def test_counter_numbers_come_from_code() -> None:
    game = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="counter")],
    )
    game.start(жадность=50, вежливость=40)

    view = game.submit("предложить 500000 20")

    assert view.ended is False
    assert view.investor_offer is not None
    assert view.investor_offer.kind == "раунд"
    assert view.investor_offer.amount == 415_000
    assert view.investor_offer.share == 20


def test_reject_keeps_the_table_open() -> None:
    game = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="reject")],
    )
    game.start(жадность=50, вежливость=40)

    view = game.submit("предложить 100000 20")

    assert view.ended is False
    assert view.outcome is None


def test_over_budget_round_is_not_accepted_or_proposed() -> None:
    game = _game(
        speeches=[NEUTRAL_SPEECH, NEUTRAL_SPEECH],
        reactions=[
            ReactionJudgement(accept=4, reaction="accept"),
            ReactionJudgement(accept=0, reaction="counter"),
        ],
        budget=800_000,
    )
    game.start(жадность=50, вежливость=40)

    rejected = game.submit("предложить 900000 20")
    assert rejected.outcome != "раунд"
    assert rejected.ended is False

    countered = game.submit("предложить 900000 25")
    assert countered.investor_offer is not None
    assert countered.investor_offer.kind == "раунд"
    assert countered.investor_offer.amount <= 800_000


def test_low_morality_blocks_round_accept_and_counter() -> None:
    game = _game(
        speeches=[NEUTRAL_SPEECH, NEUTRAL_SPEECH],
        reactions=[
            ReactionJudgement(accept=4, reaction="accept"),
            ReactionJudgement(accept=0, reaction="counter"),
        ],
        morality=20,
    )
    game.start(жадность=50, вежливость=40)

    accepted = game.submit("предложить 100000 20")
    assert accepted.outcome != "раунд"

    countered = game.submit("предложить 120000 25")
    assert countered.investor_offer is None or countered.investor_offer.kind != "раунд"


def test_slightly_unprofitable_round_can_still_be_accepted() -> None:
    game = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=3, reaction="reject")],
    )
    game.start(жадность=50, вежливость=40)

    view = game.submit("предложить 500000 10")

    assert view.outcome == "раунд"
    assert view.ended is True
