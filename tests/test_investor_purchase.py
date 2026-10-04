from invest_games.game import Game
from invest_games.ports import ReactionJudgement, SpeechJudgement
from tests.fakes import NEUTRAL_SPEECH, TALK, ScriptedBrain, ScriptedVoice
from tests.scenarios import scenario


def _game(
    *,
    speeches: list[SpeechJudgement],
    reactions: list[ReactionJudgement],
    greed: int,
    technique: int = 75,
    morality: int = 70,
) -> Game:
    game = Game(
        brain=ScriptedBrain(speeches=speeches, reactions=reactions),
        voice=ScriptedVoice("За столом."),
        scenario=scenario(technique=technique, morality=morality),
    )
    game.start(жадность=greed, вежливость=40)
    return game


def test_investor_purchase_needs_strong_technique_and_advantage() -> None:
    weak = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="purchase")],
        greed=40,
        technique=65,
    )
    closed = weak.submit("предложить 100000 20")
    assert closed.investor_offer is None or closed.investor_offer.kind != "покупка"

    strong = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="purchase")],
        greed=40,
        technique=75,
    )
    opened = strong.submit("предложить 100000 20")
    assert opened.investor_offer is not None
    assert opened.investor_offer.kind == "покупка"


def test_investor_purchase_price_is_below_valuation_and_falls_with_greed() -> None:
    mild = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="purchase")],
        greed=40,
    )
    low = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="purchase")],
        greed=80,
    )
    mild_offer = mild.submit("предложить 100000 40").investor_offer
    low_offer = low.submit("предложить 100000 40").investor_offer
    assert mild_offer is not None and low_offer is not None
    assert mild_offer.kind == "покупка"
    assert low_offer.kind == "покупка"
    assert mild_offer.amount < 1_000_000
    assert low_offer.amount < mild_offer.amount
    assert mild_offer.amount == 682_000
    assert low_offer.amount == 666_500


def test_greed_below_65_is_not_ultimatum() -> None:
    game = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="purchase")],
        greed=64,
    )
    view = game.submit("предложить 100000 20")
    assert view.ultimatum is False


def test_mid_greed_is_ultimatum_even_with_low_morality() -> None:
    game = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="purchase")],
        greed=70,
        morality=20,
    )
    view = game.submit("предложить 100000 40")
    assert view.investor_offer is not None
    assert view.investor_offer.kind == "покупка"
    assert view.ultimatum is True


def test_very_greedy_low_morality_drops_ultimatum() -> None:
    game = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="purchase")],
        greed=90,
        morality=20,
    )
    view = game.submit("предложить 100000 40")
    assert view.investor_offer is not None
    assert view.investor_offer.kind == "покупка"
    assert view.ultimatum is False


def test_no_consent_on_ultimatum_is_founder_refusal() -> None:
    game = Game(
        brain=ScriptedBrain(
            speeches=[
                NEUTRAL_SPEECH,
                SpeechJudgement(
                    tone=1,
                    competence=1,
                    believe_facts=False,
                    tech_shift=0,
                    burn_patience=False,
                    founder_accepts=False,
                ),
            ],
            reactions=[ReactionJudgement(accept=0, reaction="purchase")],
        ),
        voice=ScriptedVoice("За столом."),
        scenario=scenario(technique=75, morality=70),
    )
    game.start(жадность=70, вежливость=40)
    game.submit("предложить 100000 40")

    view = game.submit("нет, давайте вернёмся к раунду")

    assert view.outcome == "отказ основателя"
    assert view.ended is True


def test_low_morality_does_not_block_ordinary_purchase() -> None:
    game = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="purchase")],
        greed=40,
        morality=20,
        technique=75,
    )
    view = game.submit("предложить 100000 20")
    assert view.investor_offer is not None
    assert view.investor_offer.kind == "покупка"
    assert view.ultimatum is False


def test_ask_is_not_the_advantage_yardstick() -> None:
    brain = ScriptedBrain(
        speeches=[
            SpeechJudgement(
                tone=2,
                competence=3,
                believe_facts=True,
                tech_shift=3,
                burn_patience=False,
                founder_accepts=False,
            ),
            NEUTRAL_SPEECH,
        ],
        reactions=[TALK, ReactionJudgement(accept=4, reaction="talk")],
    )
    game = Game(
        brain=brain,
        voice=ScriptedVoice("За столом."),
        scenario=scenario(technique=50, morality=70),
    )
    game.start(жадность=40, вежливость=40)
    game.submit("у нас свой движок маршрутов")

    view = game.submit("предложить покупка 1050000")

    assert view.outcome == "покупка"
