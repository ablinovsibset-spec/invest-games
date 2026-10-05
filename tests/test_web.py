from fastapi.testclient import TestClient

from invest_games.ports import OpeningBelief, ReactionJudgement
from invest_games.web import create_app
from tests.fakes import NEUTRAL_SPEECH, ScriptedBrain, ScriptedParty, ScriptedVoice


def _client(*, party: ScriptedParty | None = None) -> TestClient:
    app = create_app(
        brain=ScriptedBrain(
            speeches=[NEUTRAL_SPEECH],
            reactions=[ReactionJudgement(accept=0, reaction="talk")],
            openings=[OpeningBelief(technique=55, morality=70)],
        ),
        voice=ScriptedVoice(["Первая реплика.", "Вторая партия."]),
        party=party
        or ScriptedParty(
            {
                "company_name": "Aurora",
                "pitch": "Ночной диспетчер для малых складов.",
                "ask": 1_000_000,
            }
        ),
    )
    return TestClient(app)


def test_start_has_sliders_then_one_field() -> None:
    client = _client()
    start = client.get("/")
    assert start.status_code == 200
    assert 'name="greed"' in start.text
    assert 'name="politeness"' in start.text
    assert 'min="0"' in start.text
    assert 'max="100"' in start.text
    assert 'name="line"' not in start.text

    table = client.post("/start", data={"greed": "40", "politeness": "60"}, follow_redirects=True)
    assert 'name="line"' in table.text
    assert 'type="number"' not in table.text
    assert "Принять" not in table.text
    assert "Aurora" in table.text
    assert "Nimbus" not in table.text


def test_refresh_does_not_open_a_new_deal() -> None:
    client = _client()
    first = client.post("/start", data={"greed": "40", "politeness": "60"}, follow_redirects=True)
    assert "Первая реплика." in first.text
    assert "Aurora" in first.text
    refresh = client.get("/")
    assert "Первая реплика." in refresh.text
    assert "Вторая партия." not in refresh.text
    assert "Aurora" in refresh.text


def test_other_browser_gets_another_live_company() -> None:
    drafts = iter(
        [
            {
                "company_name": "Aurora",
                "pitch": "Первая живая Компания.",
                "ask": 1_000_000,
            },
            {
                "company_name": "Helix",
                "pitch": "Вторая живая Компания.",
                "ask": 2_000_000,
            },
        ]
    )

    class RotatingParty:
        def __init__(self) -> None:
            self.states: list[dict[str, object]] = []

        def compose(self, state: dict[str, object]):
            from invest_games.ports import CompanyDraft

            self.states.append(state)
            return CompanyDraft.model_validate(next(drafts))

    brain = ScriptedBrain(
        speeches=[NEUTRAL_SPEECH, NEUTRAL_SPEECH],
        reactions=[ReactionJudgement(accept=0, reaction="talk")],
        openings=[
            OpeningBelief(technique=55, morality=70),
            OpeningBelief(technique=60, morality=65),
        ],
    )
    app = create_app(
        brain=brain,
        voice=ScriptedVoice(["Первая реплика.", "Вторая реплика."]),
        party=RotatingParty(),
    )
    first = TestClient(app)
    second = TestClient(app)

    one = first.post("/start", data={"greed": "40", "politeness": "60"}, follow_redirects=True)
    two = second.post("/start", data={"greed": "40", "politeness": "60"}, follow_redirects=True)

    assert "Aurora" in one.text
    assert "Helix" in two.text
    assert "Helix" not in one.text
    assert "Aurora" not in two.text


def test_web_uses_the_same_parser_and_hides_private_fields() -> None:
    client = _client()
    client.post("/start", data={"greed": "40", "politeness": "60"})
    moved = client.post("/move", data={"line": "уйти"}, follow_redirects=True)
    assert "отказ основателя" in moved.text.casefold()
    assert "Оценка" not in moved.text
    assert "Техника" not in moved.text
    assert "Мораль" not in moved.text
    assert "Бюджет" not in moved.text
    assert 'name="line"' not in moved.text


def test_ended_table_does_not_take_another_move() -> None:
    client = _client()
    client.post("/start", data={"greed": "40", "politeness": "60"})
    client.post("/move", data={"line": "уйти"})
    again = client.post("/move", data={"line": "ещё слово"})
    assert "закрыт" in again.text.casefold()
    assert "ещё слово" not in again.text
