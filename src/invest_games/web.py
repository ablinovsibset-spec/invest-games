from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from invest_games.game import ApiError, Game, InputError, View
from invest_games.ports import Brain, Voice
from invest_games.settings import require_routerai_key

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def create_app(brain: Brain | None = None, voice: Voice | None = None) -> FastAPI:
    if brain is None or voice is None:
        require_routerai_key()
        from invest_games.live import JevBrain, LlmVoice

        brain = brain or JevBrain()
        voice = voice or LlmVoice()

    app = FastAPI()
    tables: dict[str, tuple[Game, View]] = {}

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse:
        deal_id = request.cookies.get("deal_id")
        session = tables.get(deal_id or "")
        if session is None:
            return TEMPLATES.TemplateResponse(request, "start.html")
        _game, view = session
        return TEMPLATES.TemplateResponse(
            request,
            "table.html",
            {"view": view, "error": None},
        )

    @app.post("/start")
    def start(
        request: Request,
        greed: int = Form(...),
        politeness: int = Form(...),
    ) -> RedirectResponse:
        deal_id = request.cookies.get("deal_id")
        if deal_id and deal_id in tables:
            return RedirectResponse("/", status_code=303)
        game = Game(brain=brain, voice=voice)
        view = game.start(жадность=greed, вежливость=politeness)
        deal_id = str(uuid.uuid4())
        tables[deal_id] = (game, view)
        response = RedirectResponse("/", status_code=303)
        response.set_cookie("deal_id", deal_id)
        return response

    @app.post("/move")
    def move(request: Request, line: str = Form(...)) -> Response:
        deal_id = request.cookies.get("deal_id")
        session = tables.get(deal_id or "")
        if session is None:
            return RedirectResponse("/", status_code=303)
        game, view = session
        error = None
        if view.ended:
            error = "Стол закрыт: партия уже закончилась"
        else:
            try:
                view = game.submit(line)
                tables[deal_id or ""] = (game, view)
            except (InputError, ApiError) as exc:
                error = exc.message
                view = game.view()
        return TEMPLATES.TemplateResponse(
            request,
            "table.html",
            {"view": view, "error": error},
        )

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
