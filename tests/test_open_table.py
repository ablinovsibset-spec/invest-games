import io

from invest_games.cli import play
from invest_games.game import Game, InputError, View
from invest_games.scenario import Scenario

from tests.fakes import ScriptedBrain, ScriptedVoice


NORMAL = Scenario(
    company_name="Nimbus",
    pitch="Складской помощник с живым интерфейсом для кладовщиков.",
    ask=1_000_000,
    budget=800_000,
    technique=50,
    morality=70,
)

LOW_MORAL = Scenario(
    company_name="Nimbus",
    pitch="Складской помощник с живым интерфейсом для кладовщиков.",
    ask=1_000_000,
    budget=800_000,
    technique=50,
    morality=20,
)


def _open_fields(view: View) -> set[str]:
    return set(view.__dataclass_fields__)


def test_start_shows_pitch_ask_patience_and_first_line() -> None:
    voice = ScriptedVoice("Готов сесть за стол на этих цифрах.")
    game = Game(brain=ScriptedBrain(), voice=voice, scenario=NORMAL)

    view = game.start(жадность=40, вежливость=60)

    assert view.company_name == "Nimbus"
    assert view.pitch == NORMAL.pitch
    assert view.ask == 1_000_000
    assert view.patience == 4
    assert view.greed == 40
    assert view.politeness == 60
    assert view.remarks[-1].speaker == "инвестор"
    assert view.remarks[-1].text == "Готов сесть за стол на этих цифрах."
    assert view.ended is False
    assert view.outcome is None


def test_normal_morality_opens_with_greed_round_inside_budget() -> None:
    game = Game(
        brain=ScriptedBrain(),
        voice=ScriptedVoice("Раунд на столе."),
        scenario=NORMAL,
    )

    view = game.start(жадность=50, вежливость=40)

    assert view.investor_offer is not None
    assert view.investor_offer.kind == "раунд"
    assert view.investor_offer.amount == 150_000
    assert view.investor_offer.share == 20
    assert view.investor_offer.amount <= 800_000


def test_low_morality_opens_without_round() -> None:
    game = Game(
        brain=ScriptedBrain(),
        voice=ScriptedVoice("Не партнёрствую с этим активом."),
        scenario=LOW_MORAL,
    )

    view = game.start(жадность=50, вежливость=40)

    assert view.investor_offer is None


def test_open_view_hides_valuation_technique_morality_budget() -> None:
    game = Game(
        brain=ScriptedBrain(),
        voice=ScriptedVoice("Цифры на столе."),
        scenario=NORMAL,
    )

    view = game.start(жадность=30, вежливость=20)
    names = _open_fields(view)

    assert "valuation" not in names
    assert "technique" not in names
    assert "morality" not in names
    assert "budget" not in names
    assert "оценка" not in {name.casefold() for name in names}
    assert "техника" not in {name.casefold() for name in names}
    assert "мораль" not in {name.casefold() for name in names}
    assert "бюджет" not in {name.casefold() for name in names}


def test_leave_and_quit_are_founder_refusal_and_close_the_table() -> None:
    game = Game(
        brain=ScriptedBrain(),
        voice=ScriptedVoice("Открылись."),
        scenario=NORMAL,
    )
    game.start(жадность=20, вежливость=20)

    left = game.submit("уйти")
    assert left.outcome == "отказ основателя"
    assert left.ended is True

    game = Game(
        brain=ScriptedBrain(),
        voice=ScriptedVoice("Открылись."),
        scenario=NORMAL,
    )
    game.start(жадность=20, вежливость=20)
    quit_view = game.submit("QUIT")
    assert quit_view.outcome == "отказ основателя"
    assert quit_view.ended is True


def test_after_outcome_submit_is_rejected() -> None:
    game = Game(
        brain=ScriptedBrain(),
        voice=ScriptedVoice("Открылись."),
        scenario=NORMAL,
    )
    game.start(жадность=20, вежливость=20)
    game.submit("уйти")

    try:
        game.submit("ещё слово")
    except InputError as error:
        assert "закрыт" in error.message.casefold()
    else:
        raise AssertionError("closed table accepted a move")


def test_console_sets_traits_shows_table_and_leaves() -> None:
    game = Game(
        brain=ScriptedBrain(),
        voice=ScriptedVoice("Первая реплика за столом."),
        scenario=NORMAL,
    )
    stdout = io.StringIO()

    play(game, stdin=io.StringIO("40\n60\nуйти\n"), stdout=stdout)

    out = stdout.getvalue()
    assert "Складской помощник" in out
    assert "1000000" in out.replace(" ", "").replace("€", "")
    assert "Первая реплика за столом" in out
    assert "отказ основателя" in out.casefold()
