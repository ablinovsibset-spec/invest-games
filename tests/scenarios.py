from invest_games.scenario import Scenario


def scenario(
    *,
    technique: int = 50,
    morality: int = 70,
    ask: int = 1_000_000,
    budget: int = 800_000,
) -> Scenario:
    return Scenario(
        company_name="Nimbus",
        pitch="Складской помощник с живым интерфейсом для кладовщиков.",
        ask=ask,
        budget=budget,
        technique=technique,
        morality=morality,
    )
