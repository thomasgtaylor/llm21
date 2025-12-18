import os
from dataclasses import dataclass
from functools import cache
from typing import Annotated, TypedDict, cast

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from blackjack import Game, Hand

load_dotenv()

PROMPT_TEMPLATE = """Your hand: {hand} ({hand_value})
Dealer shows: {dealer_upcard}
Available actions: {actions}

What is the optimal play?"""


class DecisionResponse(TypedDict):
    decision: Annotated[str, ..., "The optimal blackjack decision."]


@cache
def get_model():
    model_name = os.getenv("MODEL")
    if not model_name:
        raise ValueError("MODEL environment variable not set")
    return init_chat_model(model_name, max_retries=25).with_structured_output(
        DecisionResponse
    )


@dataclass
class Recommendation:
    decision: str


def build_prompt(hand: Hand, dealer_upcard: str) -> str:
    actions = ["hit", "stand"]
    if hand.can_double:
        actions.append("double")
    if hand.can_split:
        actions.append("split")
    if hand.can_surrender:
        actions.append("surrender")

    return PROMPT_TEMPLATE.format(
        hand=hand,
        hand_value=hand.value,
        dealer_upcard=dealer_upcard,
        actions=", ".join(actions),
    )


async def get_recommendation(game: Game) -> Recommendation | None:
    if not game.round_active or not game.current_hand:
        return None

    hand = game.current_hand
    dealer_upcard = str(game.dealer_hand.cards[0])

    prompt = build_prompt(hand, dealer_upcard)
    response = await get_model().ainvoke(prompt)
    response = cast(DecisionResponse, response)

    return Recommendation(decision=response["decision"])
