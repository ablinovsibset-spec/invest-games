from fastapi.testclient import TestClient

from invest_games.ports import OpeningBelief, ReactionJudgement
from invest_games.web import create_app
from tests.fakes import NEUTRAL_SPEECH, ScriptedBrain, ScriptedVoice


START = {
    "greed": "40",
    "politeness": "60",
    "company_name": "Aurora",
    "pitch": "Ночной диспетчер для малых складов.",
    "ask": "1000000",
}


def _client() -> TestClient:
    app = create_app(
        brain=ScriptedBrain(
            speeches=[NEUTRAL_SPEECH],
            reactions=[ReactionJudgement(accept=0, reaction="talk")],
            openings=[OpeningBelief(technique=55, morality=70)],
        ),
        voice=ScriptedVoice(["Первая реплика.", "Вторая реплика."]),
    )
    return TestClient(app)


def test_start_has_traits_and_company_then_one_field() -> None:
    client = _client()
    start = client.get("/")
    assert start.status_code == 200
    assert 'name="greed"' in start.text
    assert 'name="politeness"' in start.text
    assert 'name="company_name"' in start.text
    assert 'name="pitch"' in start.text
    assert 'name="ask"' in start.text
    assert 'min="0"' in start.text
    assert 'max="100"' in start.text
    assert 'name="line"' not in start.text

    table = client.post("/start", data=START, follow_redirects=True)
    assert 'name="line"' in table.text
    assert "Принять" not in table.text
    assert "Aurora" in table.text
    assert "Nimbus" not in table.text


def test_refresh_does_not_open_a_new_deal() -> None:
    client = _client()
    first = client.post("/start", data=START, follow_redirects=True)
    assert "Первая реплика." in first.text
    assert "Aurora" in first.text
    refresh = client.get("/")
    assert "Первая реплика." in refresh.text
    assert "Вторая реплика." not in refresh.text
    assert "Aurora" in refresh.text


def test_other_browser_gets_another_founder_company() -> None:
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
    )
    first = TestClient(app)
    second = TestClient(app)

    one = first.post(
        "/start",
        data={
            **START,
            "company_name": "Aurora",
            "pitch": "Первая живая Компания.",
        },
        follow_redirects=True,
    )
    two = second.post(
        "/start",
        data={
            **START,
            "company_name": "Helix",
            "pitch": "Вторая живая Компания.",
            "ask": "2000000",
        },
        follow_redirects=True,
    )

    assert "Aurora" in one.text
    assert "Helix" in two.text
    assert "Helix" not in one.text
    assert "Aurora" not in two.text


def test_web_uses_the_same_parser_and_hides_private_fields() -> None:
    client = _client()
    client.post("/start", data=START)
    moved = client.post("/move", data={"line": "уйти"}, follow_redirects=True)
    assert "отказ основателя" in moved.text.casefold()
    assert "Оценка" not in moved.text
    assert "Техника" not in moved.text
    assert "Мораль" not in moved.text
    assert "Бюджет" not in moved.text
    assert 'name="line"' not in moved.text


def test_ended_table_does_not_take_another_move() -> None:
    client = _client()
    client.post("/start", data=START)
    client.post("/move", data={"line": "уйти"})
    again = client.post("/move", data={"line": "ещё слово"})
    assert "закрыт" in again.text.casefold()
    assert "ещё слово" not in again.text


def test_bad_ask_stays_on_start() -> None:
    client = _client()
    bad = client.post(
        "/start",
        data={**START, "ask": "100"},
        follow_redirects=True,
    )
    assert bad.status_code == 400
    assert "Запрос" in bad.text
    assert 'name="company_name"' in bad.text
    assert 'name="line"' not in bad.text


def test_open_new_table_clears_deal_and_shows_blank_start() -> None:
    client = _client()
    table = client.post("/start", data=START, follow_redirects=True)
    assert "Открыть новый стол" in table.text
    assert "confirm(" in table.text
    assert "Aurora" in table.text

    start = client.post("/new-table", follow_redirects=True)
    assert start.status_code == 200
    assert 'name="company_name"' in start.text
    assert 'name="line"' not in start.text
    assert "Aurora" not in start.text
    assert "Открыть новый стол" not in start.text
