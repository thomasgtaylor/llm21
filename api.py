from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from blackjack import Game
from llm import get_recommendation
from strategy import get_optimal_play

app = FastAPI()
templates = Jinja2Templates(directory="templates")

game = Game()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "game": game},
    )


@app.post("/deal", response_class=HTMLResponse)
async def deal(request: Request):
    game.deal()
    return templates.TemplateResponse(
        "partials/game.html",
        {"request": request, "game": game},
    )


@app.post("/hit", response_class=HTMLResponse)
async def hit(request: Request):
    game.hit()
    return templates.TemplateResponse(
        "partials/game.html",
        {"request": request, "game": game},
    )


@app.post("/stand", response_class=HTMLResponse)
async def stand(request: Request):
    game.stand()
    return templates.TemplateResponse(
        "partials/game.html",
        {"request": request, "game": game},
    )


@app.post("/double", response_class=HTMLResponse)
async def double(request: Request):
    game.double_down()
    return templates.TemplateResponse(
        "partials/game.html",
        {"request": request, "game": game},
    )


@app.post("/split", response_class=HTMLResponse)
async def split(request: Request):
    game.split()
    return templates.TemplateResponse(
        "partials/game.html",
        {"request": request, "game": game},
    )


@app.post("/surrender", response_class=HTMLResponse)
async def surrender(request: Request):
    game.surrender()
    return templates.TemplateResponse(
        "partials/game.html",
        {"request": request, "game": game},
    )


@app.get("/optimal", response_class=HTMLResponse)
async def optimal_play(request: Request):
    optimal = None
    if game.round_active and game.current_hand:
        optimal = get_optimal_play(game.current_hand, game.dealer_hand)
    return templates.TemplateResponse(
        "partials/optimal.html",
        {"request": request, "optimal": optimal},
    )


@app.get("/llm", response_class=HTMLResponse)
async def llm_recommendation(request: Request):
    recommendation = await get_recommendation(game)
    return templates.TemplateResponse(
        "partials/llm.html",
        {"request": request, "recommendation": recommendation},
    )
