from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    company_name: str
    pitch: str
    ask: int
    budget: int
    technique: int
    morality: int


DEFAULT_SCENARIO = Scenario(
    company_name="Nimbus",
    pitch=(
        "Складской помощник с живым интерфейсом для кладовщиков. "
        "Команда рассказывает про свой движок маршрутов и обещает меньше потерь на полке."
    ),
    ask=2_000_000,
    budget=700_000,
    technique=55,
    morality=70,
)
