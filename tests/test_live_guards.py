from invest_games.cli import main
from invest_games.game import ApiError, Game, InputError
from invest_games.ports import ReactionJudgement, SpeechJudgement
from invest_games.web import create_app
from tests.fakes import NEUTRAL_SPEECH, TALK, BoomPort, ScriptedBrain, ScriptedVoice
from tests.scenarios import scenario


def test_console_does_not_start_without_key(monkeypatch) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    try:
        main([])
    except SystemExit as exit_code:
        assert exit_code.code != 0
    else:
        raise AssertionError("console started without a key")


def test_web_does_not_start_without_key(monkeypatch) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    try:
        create_app()
    except SystemExit:
        return
    raise AssertionError("web started without a key")


def test_start_voice_failure_does_not_leave_a_table() -> None:
    game = Game(brain=ScriptedBrain(), voice=BoomPort(), scenario=scenario())
    try:
        game.start(жадность=20, вежливость=20)
    except ApiError:
        pass
    else:
        raise AssertionError("voice failure was swallowed")
    try:
        game.view()
    except InputError:
        return
    raise AssertionError("start left a table after voice failure")


def test_voice_hears_the_decided_accept_not_the_raw_reaction() -> None:
    voice = ScriptedVoice(["Открылись.", "Берём."])
    game = Game(
        brain=ScriptedBrain(
            speeches=[NEUTRAL_SPEECH],
            reactions=[ReactionJudgement(accept=3, reaction="talk")],
        ),
        voice=voice,
        scenario=scenario(),
    )
    game.start(жадность=50, вежливость=40)
    view = game.submit("предложить 100000 20")
    assert view.outcome == "раунд"
    assert voice.states[-1]["reaction"] == "accept"


def test_routerai_failure_does_not_burn_patience_and_allows_retry() -> None:
    voice = ScriptedVoice("Открылись.")
    boom = BoomPort()
    game = Game(brain=boom, voice=voice, scenario=scenario())
    opened = game.start(жадность=20, вежливость=20)
    assert opened.patience == 2

    try:
        game.submit("извините за паузу")
    except ApiError as error:
        assert "стол не изменился" in error.message.casefold()
    else:
        raise AssertionError("network failure was swallowed")

    assert game.view().patience == 2
    assert game.view().ended is False
    assert len(game.view().remarks) == 1

    game = Game(
        brain=ScriptedBrain(
            speeches=[NEUTRAL_SPEECH],
            reactions=[ReactionJudgement(accept=0, reaction="talk")],
        ),
        voice=voice,
        scenario=scenario(),
    )
    game.start(жадность=20, вежливость=20)
    retry = game.submit("извините за паузу")
    assert retry.ended is False
    assert retry.patience == 2


def test_second_jev_sees_updated_technique_and_valuation() -> None:
    brain = ScriptedBrain(
        speeches=[
            SpeechJudgement(
                tone=2,
                competence=3,
                believe_facts=True,
                tech_shift=2,
                burn_patience=False,
                founder_accepts=False,
            )
        ],
        reactions=[TALK],
    )
    game = Game(brain=brain, voice=ScriptedVoice("За столом."), scenario=scenario(technique=50))
    game.start(жадность=50, вежливость=40)
    game.submit("предложить 100000 20")

    before = brain.speech_states[0]
    after = brain.reaction_states[0]
    before_tech = before["technique"]
    after_tech = after["technique"]
    assert isinstance(before_tech, int)
    assert isinstance(after_tech, int)
    assert after_tech == before_tech + 10
    assert after["valuation"] != before["valuation"]
