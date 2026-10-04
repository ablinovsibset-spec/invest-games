from invest_games.game import Game
from invest_games.ports import ReactionJudgement, SpeechJudgement
from tests.fakes import NEUTRAL_SPEECH, TALK, ScriptedBrain, ScriptedVoice
from tests.scenarios import scenario


def test_fat_offer_can_open_purchase_on_the_same_turn() -> None:
    game = Game(
        brain=ScriptedBrain(
            speeches=[
                SpeechJudgement(
                    tone=3,
                    competence=3,
                    believe_facts=True,
                    tech_shift=1,
                    burn_patience=False,
                    founder_accepts=False,
                )
            ],
            reactions=[ReactionJudgement(accept=0, reaction="purchase")],
        ),
        voice=ScriptedVoice("За столом."),
        scenario=scenario(technique=65),
    )
    game.start(жадность=50, вежливость=40)

    view = game.submit("предложить 100000 20")

    assert view.investor_offer is not None
    assert view.investor_offer.kind == "покупка"


def test_anchor_does_not_make_valuation_equal_implied() -> None:
    game = Game(
        brain=ScriptedBrain(
            speeches=[NEUTRAL_SPEECH, NEUTRAL_SPEECH],
            reactions=[TALK, ReactionJudgement(accept=4, reaction="talk")],
        ),
        voice=ScriptedVoice("За столом."),
        scenario=scenario(technique=50),
    )
    game.start(жадность=50, вежливость=40)
    game.submit("предложить 800000 5")

    view = game.submit("предложить покупка 15999999")

    assert view.outcome != "покупка"
    assert view.ended is False


def test_investor_counter_does_not_invent_a_purchase() -> None:
    game = Game(
        brain=ScriptedBrain(
            speeches=[NEUTRAL_SPEECH, NEUTRAL_SPEECH],
            reactions=[
                ReactionJudgement(accept=0, reaction="counter"),
                ReactionJudgement(accept=0, reaction="purchase"),
            ],
        ),
        voice=ScriptedVoice("За столом."),
        scenario=scenario(technique=75),
    )
    game.start(жадность=50, вежливость=40)
    game.submit("предложить 100000 5")

    view = game.submit("ну подумаем")

    assert view.investor_offer is None or view.investor_offer.kind != "покупка"


def test_greed_does_not_cut_valuation_off_a_purchase() -> None:
    for greed in (10, 90):
        game = Game(
            brain=ScriptedBrain(
                speeches=[NEUTRAL_SPEECH],
                reactions=[ReactionJudgement(accept=4, reaction="talk")],
            ),
            voice=ScriptedVoice("За столом."),
            scenario=scenario(technique=75),
        )
        game.start(жадность=greed, вежливость=40)
        view = game.submit("предложить покупка 900000")
        assert view.outcome == "покупка", greed


def test_open_view_still_hides_private_numbers() -> None:
    game = Game(
        brain=ScriptedBrain(
            speeches=[
                SpeechJudgement(
                    tone=3,
                    competence=3,
                    believe_facts=True,
                    tech_shift=2,
                    burn_patience=False,
                    founder_accepts=False,
                )
            ],
            reactions=[ReactionJudgement(accept=0, reaction="purchase")],
        ),
        voice=ScriptedVoice("За столом."),
        scenario=scenario(technique=75),
    )
    game.start(жадность=40, вежливость=40)
    view = game.submit("предложить 100000 20")
    names = set(view.__dataclass_fields__)
    assert "valuation" not in names
    assert "technique" not in names
    assert "morality" not in names
    assert "budget" not in names
