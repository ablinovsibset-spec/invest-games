from __future__ import annotations

import sys
from typing import TextIO

from invest_games.game import ApiError, Game, InputError, View
from invest_games.settings import require_routerai_key


def play(game: Game, stdin: TextIO, stdout: TextIO) -> None:
    try:
        stdout.write("Жадность (0-100): ")
        stdout.flush()
        greed = int(stdin.readline().strip())
        stdout.write("Вежливость (0-100): ")
        stdout.flush()
        politeness = int(stdin.readline().strip())
        view = game.start(жадность=greed, вежливость=politeness)
        _print_view(view, stdout)
        while not view.ended:
            stdout.write("> ")
            stdout.flush()
            line = stdin.readline()
            if not line:
                break
            try:
                view = game.submit(line)
            except InputError as error:
                stdout.write(f"{error.message}\n")
                continue
            except ApiError as error:
                stdout.write(f"{error.message}\n")
                continue
            _print_view(view, stdout)
    except KeyboardInterrupt:
        stdout.write("\n")
        stdout.flush()


def _print_view(view: View, stdout: TextIO) -> None:
    stdout.write(f"Компания: {view.company_name}\n")
    stdout.write(f"Питч: {view.pitch}\n")
    stdout.write(f"Запрос: {view.ask}\n")
    stdout.write(f"Терпение: {view.patience}\n")
    stdout.write(f"Жадность: {view.greed}\n")
    stdout.write(f"Вежливость: {view.politeness}\n")
    if view.investor_offer is not None:
        stdout.write(f"Предложение Инвестора: {_format_offer(view.investor_offer)}\n")
    if view.founder_offer is not None:
        stdout.write(f"Предложение Основателя: {_format_offer(view.founder_offer)}\n")
    if view.ultimatum:
        stdout.write("Ультиматум: да\n")
    for remark in view.remarks:
        who = "Инвестор" if remark.speaker == "инвестор" else "Основатель"
        stdout.write(f"{who}: {remark.text}\n")
    if view.outcome is not None:
        stdout.write(f"Исход: {view.outcome}\n")


def _format_offer(offer) -> str:
    if offer.kind == "покупка":
        return f"Покупка {offer.amount}"
    return f"Раунд {offer.amount} за {offer.share}%"


def main(argv: list[str] | None = None) -> None:
    del argv
    require_routerai_key()
    from invest_games.live import JevBrain, LlmVoice

    play(Game(brain=JevBrain(), voice=LlmVoice()), stdin=sys.stdin, stdout=sys.stdout)


if __name__ == "__main__":
    main()
