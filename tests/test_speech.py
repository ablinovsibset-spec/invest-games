from invest_games.game import Game, InputError
from invest_games.ports import ReactionJudgement, SpeechJudgement
from tests.fakes import NEUTRAL_SPEECH, TALK, ScriptedBrain, ScriptedVoice
from tests.scenarios import scenario


def _game(
    *,
    speeches: list[SpeechJudgement],
    reactions: list[ReactionJudgement] | None = None,
    technique: int = 50,
    morality: int = 70,
) -> Game:
    return Game(
        brain=ScriptedBrain(speeches=speeches, reactions=reactions or []),
        voice=ScriptedVoice("За столом."),
        scenario=scenario(technique=technique, morality=morality),
    )


def test_plain_line_is_speech_and_does_not_place_offer() -> None:
    game = _game(speeches=[NEUTRAL_SPEECH], reactions=[TALK])
    game.start(жадность=40, вежливость=40)

    view = game.submit("ну давай тысяч пятьсот, это же смешно")

    assert view.founder_offer is None
    assert view.ended is False
    assert view.remarks[-2].speaker == "основатель"
    assert "тысяч пятьсот" in view.remarks[-2].text


def test_without_believe_facts_polite_talk_does_not_open_purchase() -> None:
    game = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="purchase")],
        technique=65,
    )
    game.start(жадность=50, вежливость=40)

    view = game.submit("предложить 100000 20")

    assert view.investor_offer is None or view.investor_offer.kind != "покупка"
    assert view.outcome != "покупка"


def test_speech_does_not_turn_low_morality_into_a_round() -> None:
    game = _game(
        speeches=[
            SpeechJudgement(
                tone=3,
                competence=3,
                believe_facts=True,
                tech_shift=3,
                burn_patience=False,
                founder_accepts=False,
            )
        ],
        reactions=[ReactionJudgement(accept=4, reaction="accept")],
        morality=20,
    )
    game.start(жадность=50, вежливость=40)

    view = game.submit("предложить 100000 20")

    assert view.outcome != "раунд"
    assert view.investor_offer is None or view.investor_offer.kind != "раунд"


def test_burned_patience_is_visible() -> None:
    game = _game(
        speeches=[
            SpeechJudgement(
                tone=0,
                competence=1,
                believe_facts=False,
                tech_shift=0,
                burn_patience=True,
                founder_accepts=False,
            )
        ],
        reactions=[TALK],
    )
    opened = game.start(жадность=20, вежливость=20)
    assert opened.patience == 2

    view = game.submit("простите за паузу")

    assert view.patience == 1
    assert view.ended is False


def test_zero_patience_is_exhaustion_without_second_jev() -> None:
    brain = ScriptedBrain(
        speeches=[
            SpeechJudgement(
                tone=0,
                competence=0,
                believe_facts=False,
                tech_shift=0,
                burn_patience=True,
                founder_accepts=False,
            )
        ],
        reactions=[ReactionJudgement(accept=4, reaction="accept")],
    )
    game = Game(
        brain=brain,
        voice=ScriptedVoice("За столом."),
        scenario=scenario(),
    )
    game.start(жадность=20, вежливость=0)

    view = game.submit("ещё одно слово")

    assert view.outcome == "исчерпание"
    assert view.ended is True
    assert brain.reaction_states == []


def test_walk_away_while_patience_remains_is_not_exhaustion() -> None:
    game = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="walk_away")],
    )
    opened = game.start(жадность=20, вежливость=40)
    assert opened.patience == 3

    view = game.submit("мы ещё подумаем")

    assert view.outcome == "уход"
    assert view.ended is True
    assert view.patience == 3


def test_after_walk_or_exhaustion_moves_stop() -> None:
    game = _game(
        speeches=[NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="walk_away")],
    )
    game.start(жадность=20, вежливость=40)
    game.submit("пока")

    try:
        game.submit("ещё")
    except InputError as error:
        assert "закрыт" in error.message.casefold()
    else:
        raise AssertionError("closed table accepted a move")
