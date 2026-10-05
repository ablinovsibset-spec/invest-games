from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    company_name: str
    pitch: str
    ask: int
    budget: int
    technique: int
    morality: int
