from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

from invest_games.ports import Brain, CompanyDraft, Party, Voice
from invest_games.scenario import Scenario

LOW_MORALITY = 40
STRONG_TECHNIQUE = 70
ANCHOR_NUMERATOR = 3
ANCHOR_DENOMINATOR = 10
ACCEPT_THRESHOLD = 3
TECH_DELTA = (0, 5, 10, 15)
ASK_MIN = 200_000
ASK_MAX = 10_000_000
BUDGET_SHARE_MIN = 20
BUDGET_SHARE_MAX = 50
Outcome = Literal["раунд", "покупка", "уход", "исчерпание", "отказ основателя"]
OfferKind = Literal["раунд", "покупка"]


class InputError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ApiError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class Offer:
    kind: OfferKind
    amount: int
    share: int | None = None


@dataclass(frozen=True)
class Remark:
    speaker: Literal["основатель", "инвестор"]
    text: str


@dataclass(frozen=True)
class View:
    company_name: str
    pitch: str
    ask: int
    patience: int
    greed: int
    politeness: int
    remarks: tuple[Remark, ...]
    investor_offer: Offer | None
    founder_offer: Offer | None
    ultimatum: bool
    outcome: Outcome | None
    ended: bool


@dataclass
class _Table:
    company_name: str
    pitch: str
    ask: int
    budget: int
    technique: int
    morality: int
    valuation: int
    patience: int
    greed: int
    politeness: int
    remarks: list[Remark] = field(default_factory=list)
    investor_offer: Offer | None = None
    founder_offer: Offer | None = None
    ultimatum: bool = False
    outcome: Outcome | None = None
    advantageous: bool = False
    pending_speech: str = ""


class Game:
    def __init__(
        self,
        *,
        brain: Brain,
        voice: Voice,
        scenario: Scenario | None = None,
        party: Party | None = None,
    ) -> None:
        self._brain = brain
        self._voice = voice
        self._scenario = scenario
        self._party = party
        self._table: _Table | None = None

    def start(self, жадность: int, вежливость: int) -> View:
        greed = _trait(жадность, "Жадность")
        politeness = _trait(вежливость, "Вежливость")
        if self._scenario is not None:
            table = self._table_from_scenario(self._scenario, greed=greed, politeness=politeness)
        else:
            table = self._table_from_party(greed=greed, politeness=politeness)
        if not _low_morality(table.morality):
            table.investor_offer = _opening_round(table)
        self._table = table
        try:
            line = self._speak({"opening": True, "investor_offer": _offer_payload(table.investor_offer)})
        except ApiError:
            self._table = None
            raise
        table.remarks.append(Remark(speaker="инвестор", text=line))
        return self._view()

    def _table_from_scenario(self, scenario: Scenario, *, greed: int, politeness: int) -> _Table:
        return _Table(
            company_name=scenario.company_name,
            pitch=scenario.pitch,
            ask=scenario.ask,
            budget=scenario.budget,
            technique=scenario.technique,
            morality=scenario.morality,
            valuation=scenario.ask,
            patience=_patience(politeness),
            greed=greed,
            politeness=politeness,
        )

    def _table_from_party(self, *, greed: int, politeness: int) -> _Table:
        if self._party is None:
            raise InputError("Живой стол требует партию")
        try:
            raw = self._party.compose({"greed": greed, "politeness": politeness})
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError("Сбой RouterAI. Стол не изменился, повторите ход.") from exc
        draft = _validated_draft(raw)
        budget = draft.ask * random.randint(BUDGET_SHARE_MIN, BUDGET_SHARE_MAX) // 100
        try:
            belief = self._brain.judge_opening(
                {"company_name": draft.company_name, "pitch": draft.pitch}
            )
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError("Сбой RouterAI. Стол не изменился, повторите ход.") from exc
        return _Table(
            company_name=draft.company_name,
            pitch=draft.pitch,
            ask=draft.ask,
            budget=budget,
            technique=belief.technique,
            morality=belief.morality,
            valuation=draft.ask,
            patience=_patience(politeness),
            greed=greed,
            politeness=politeness,
        )
    def view(self) -> View:
        return self._view()

    def submit(self, строка: str) -> View:
        table = self._require_table()
        if table.outcome is not None:
            raise InputError("Стол закрыт: партия уже закончилась")
        command = parse(строка)
        if isinstance(command, _Quit):
            table.outcome = "отказ основателя"
            return self._view()
        snapshot = _snapshot(table)
        try:
            return self._play_turn(command)
        except ApiError:
            self._table = snapshot
            raise

    def _play_turn(self, command: _Speech | _FounderOffer) -> View:
        table = self._require_table()
        if isinstance(command, _FounderOffer):
            table.founder_offer = Offer(
                kind=command.kind,
                amount=command.amount,
                share=command.share,
            )
            table.pending_speech = ""
            founder_text = _offer_line(table.founder_offer)
        else:
            table.pending_speech = command.text
            founder_text = command.text
        table.remarks.append(Remark(speaker="основатель", text=founder_text))
        table.advantageous = _advantageous(table, table.founder_offer)

        speech = self._judge_speech()
        if table.ultimatum and not speech.founder_accepts:
            table.outcome = "отказ основателя"
            return self._view()
        if speech.founder_accepts and table.investor_offer is not None:
            table.outcome = _outcome_for(table.investor_offer)
            line = self._speak({"reaction": "founder_accepts", "outcome": table.outcome})
            table.remarks.append(Remark(speaker="инвестор", text=line))
            return self._view()

        if speech.believe_facts:
            delta = TECH_DELTA[speech.tech_shift]
            table.technique += delta
            table.valuation = table.valuation * (100 + delta) // 100
        if table.founder_offer is not None:
            table.valuation = _anchor(table.valuation, _implied(table.founder_offer))
        if speech.burn_patience:
            table.patience = max(0, table.patience - 1)
            if table.patience == 0:
                table.outcome = "исчерпание"
                line = self._speak({"reaction": "exhaustion", "outcome": table.outcome})
                table.remarks.append(Remark(speaker="инвестор", text=line))
                return self._view()

        judgement = self._judge_reaction()
        legal = _legal_actions(table)
        if judgement.accept >= ACCEPT_THRESHOLD and "accept" in legal:
            reaction = "accept"
            self._accept_founder()
        else:
            reaction = judgement.reaction if judgement.reaction in legal else "talk"
            self._apply_reaction(reaction)
        if table.outcome is None:
            line = self._speak(
                {
                    "reaction": reaction,
                    "investor_offer": _offer_payload(table.investor_offer),
                    "ultimatum": table.ultimatum,
                }
            )
            table.remarks.append(Remark(speaker="инвестор", text=line))
        elif table.remarks[-1].speaker != "инвестор":
            line = self._speak({"reaction": reaction, "outcome": table.outcome})
            table.remarks.append(Remark(speaker="инвестор", text=line))
        return self._view()

    def _accept_founder(self) -> None:
        table = self._require_table()
        if table.founder_offer is None:
            return
        table.outcome = _outcome_for(table.founder_offer)
        table.ultimatum = False

    def _apply_reaction(self, reaction: str) -> None:
        table = self._require_table()
        if reaction == "accept":
            self._accept_founder()
        elif reaction == "counter":
            table.investor_offer = _counter(table)
            table.ultimatum = False
        elif reaction == "purchase":
            table.investor_offer = _investor_purchase(table)
            table.ultimatum = _ultimatum(table.greed, table.morality)
        elif reaction == "walk_away":
            table.outcome = "уход"
            table.ultimatum = False
        elif reaction == "reject":
            table.ultimatum = False

    def _judge_speech(self):
        try:
            return self._brain.judge_speech(self._hidden_state())
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError("Сбой RouterAI. Стол не изменился, повторите ход.") from exc

    def _judge_reaction(self):
        try:
            return self._brain.judge_reaction(self._hidden_state(include_legal=True))
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError("Сбой RouterAI. Стол не изменился, повторите ход.") from exc

    def _speak(self, extra: dict[str, object]) -> str:
        try:
            return self._voice.speak({**self._hidden_state(), **extra})
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError("Сбой RouterAI. Стол не изменился, повторите ход.") from exc

    def _hidden_state(self, *, include_legal: bool = False) -> dict[str, object]:
        table = self._require_table()
        state: dict[str, object] = {
            "pitch": table.pitch,
            "ask": table.ask,
            "patience": table.patience,
            "greed": table.greed,
            "politeness": table.politeness,
            "technique": table.technique,
            "morality": table.morality,
            "valuation": table.valuation,
            "budget": table.budget,
            "min_share": _min_share(table.greed),
            "founder_offer": _offer_payload(table.founder_offer),
            "investor_offer": _offer_payload(table.investor_offer),
            "founder_speech": table.pending_speech,
            "advantageous": table.advantageous,
            "ultimatum": table.ultimatum,
            "history": [f"{item.speaker}: {item.text}" for item in table.remarks],
        }
        if include_legal:
            state["legal"] = _legal_actions(table)
        return state

    def _view(self) -> View:
        table = self._require_table()
        return View(
            company_name=table.company_name,
            pitch=table.pitch,
            ask=table.ask,
            patience=table.patience,
            greed=table.greed,
            politeness=table.politeness,
            remarks=tuple(table.remarks),
            investor_offer=table.investor_offer,
            founder_offer=table.founder_offer,
            ultimatum=table.ultimatum,
            outcome=table.outcome,
            ended=table.outcome is not None,
        )

    def _require_table(self) -> _Table:
        if self._table is None:
            raise InputError("Стол ещё не открыт")
        return self._table


@dataclass(frozen=True)
class _Quit:
    pass


@dataclass(frozen=True)
class _Speech:
    text: str


@dataclass(frozen=True)
class _FounderOffer:
    kind: OfferKind
    amount: int
    share: int | None = None


def parse(строка: str) -> _Quit | _Speech | _FounderOffer:
    folded = строка.strip().casefold()
    if folded in {"уйти", "quit"}:
        return _Quit()
    if folded.startswith("предложить"):
        rest = folded.removeprefix("предложить").strip()
        if rest.startswith("покупка") or rest.startswith("купить"):
            token = "покупка" if rest.startswith("покупка") else "купить"
            amount = _parse_amount(rest.removeprefix(token).strip())
            if amount is None:
                raise InputError("Не разобрал сумму Покупки")
            return _FounderOffer(kind="покупка", amount=amount)
        amount, share = _parse_round(rest)
        if amount is None or share is None:
            raise InputError("Не разобрал Раунд: нужна сумма и Доля от 1 до 99")
        return _FounderOffer(kind="раунд", amount=amount, share=share)
    return _Speech(text=строка.strip())


def _parse_round(rest: str) -> tuple[int | None, int | None]:
    parts = rest.split()
    if len(parts) < 2:
        return None, None
    share_token = parts[-1].removesuffix("%")
    if not share_token.isdigit():
        return None, None
    share = int(share_token)
    if not 1 <= share <= 99:
        return None, None
    return _parse_amount(" ".join(parts[:-1])), share


def _parse_amount(text: str) -> int | None:
    cleaned = text.strip()
    if not cleaned:
        return None
    for char in cleaned:
        if char not in "0123456789_ €\t":
            return None
    digits = "".join(char for char in cleaned if char.isdigit())
    if not digits:
        return None
    return int(digits)


def _trait(value: int, name: str) -> int:
    if not 0 <= value <= 100:
        raise InputError(f"{name} должна быть от 0 до 100")
    return value


def _validated_draft(raw: CompanyDraft | object) -> CompanyDraft:
    try:
        draft = raw if isinstance(raw, CompanyDraft) else CompanyDraft.model_validate(raw)
    except Exception as exc:
        raise ApiError("Сбой RouterAI. Стол не изменился, повторите ход.") from exc
    if not draft.company_name.strip() or not draft.pitch.strip():
        raise ApiError("Сбой RouterAI. Стол не изменился, повторите ход.")
    if not ASK_MIN <= draft.ask <= ASK_MAX:
        raise ApiError("Сбой RouterAI. Стол не изменился, повторите ход.")
    return draft


def _patience(politeness: int) -> int:
    return 1 + politeness // 20


def _min_share(greed: int) -> int:
    return 10 + greed // 5


def _low_morality(morality: int) -> bool:
    return morality < LOW_MORALITY


def _strong_technique(technique: int) -> bool:
    return technique >= STRONG_TECHNIQUE


def _opening_round(table: _Table) -> Offer:
    share = min(99, _min_share(table.greed))
    raw = table.ask * share * (200 - table.greed) // (100 * 200)
    amount = min(table.budget, max(1, raw))
    return Offer(kind="раунд", amount=amount, share=share)


def _implied(offer: Offer) -> int:
    if offer.kind == "покупка" or offer.share in (None, 0):
        return offer.amount
    return offer.amount * 100 // offer.share


def _round_advantageous(table: _Table, offer: Offer) -> bool:
    assert offer.share is not None
    return (
        _implied(offer) < table.valuation
        and offer.amount <= table.budget
        and offer.share >= _min_share(table.greed)
    )


def _advantageous(table: _Table, offer: Offer | None) -> bool:
    if offer is None:
        return False
    if offer.kind == "раунд":
        return _round_advantageous(table, offer)
    return offer.amount < table.valuation


def _can_accept(table: _Table) -> bool:
    offer = table.founder_offer
    if offer is None:
        return False
    if offer.kind == "раунд":
        return offer.amount <= table.budget and not _low_morality(table.morality)
    return offer.amount < table.valuation


def _can_counter(table: _Table) -> bool:
    offer = table.founder_offer
    if offer is None or offer.kind != "раунд":
        return False
    return not _low_morality(table.morality)


def _can_purchase(table: _Table) -> bool:
    return _strong_technique(table.technique) and table.advantageous


def _legal_actions(table: _Table) -> list[str]:
    legal = ["talk", "walk_away"]
    if table.founder_offer is not None:
        legal.append("reject")
    if _can_accept(table):
        legal.append("accept")
    if _can_counter(table):
        legal.append("counter")
    if _can_purchase(table):
        legal.append("purchase")
    return legal


def _counter(table: _Table) -> Offer:
    founder = table.founder_offer
    share = min(99, max(founder.share if founder and founder.share else 1, _min_share(table.greed)))
    base = founder.amount if founder else table.ask
    amount = min(table.budget, max(1, base * (100 - (5 + table.greed // 4)) // 100))
    return Offer(kind="раунд", amount=amount, share=share)


def _investor_purchase(table: _Table) -> Offer:
    discount_bp = 1000 + table.greed * 5
    price = table.valuation * (10_000 - discount_bp) // 10_000
    if price >= table.valuation:
        price = max(0, table.valuation - 1)
    return Offer(kind="покупка", amount=max(1, price) if table.valuation > 1 else 0)


def _ultimatum(greed: int, morality: int) -> bool:
    if greed < 65:
        return False
    if greed > 85 and _low_morality(morality):
        return False
    return True


def _anchor(valuation: int, implied: int) -> int:
    if implied == valuation:
        return valuation
    moved = valuation + (implied - valuation) * ANCHOR_NUMERATOR // ANCHOR_DENOMINATOR
    if moved == implied:
        step = 1 if implied > valuation else -1
        moved = valuation + step
    return moved


def _outcome_for(offer: Offer) -> Outcome:
    return "раунд" if offer.kind == "раунд" else "покупка"


def _offer_payload(offer: Offer | None) -> dict[str, int | str] | None:
    if offer is None:
        return None
    payload: dict[str, int | str] = {"kind": offer.kind, "amount": offer.amount}
    if offer.share is not None:
        payload["share"] = offer.share
    return payload


def _offer_line(offer: Offer) -> str:
    if offer.kind == "покупка":
        return f"предложить покупка {offer.amount}"
    return f"предложить {offer.amount} {offer.share}"


def _snapshot(table: _Table) -> _Table:
    return _Table(
        company_name=table.company_name,
        pitch=table.pitch,
        ask=table.ask,
        budget=table.budget,
        technique=table.technique,
        morality=table.morality,
        valuation=table.valuation,
        patience=table.patience,
        greed=table.greed,
        politeness=table.politeness,
        remarks=list(table.remarks),
        investor_offer=table.investor_offer,
        founder_offer=table.founder_offer,
        ultimatum=table.ultimatum,
        outcome=table.outcome,
        advantageous=table.advantageous,
        pending_speech=table.pending_speech,
    )
