import argparse
import asyncio
import csv
from dataclasses import asdict, dataclass
from typing import Awaitable, Callable

from blackjack import Game, HandResult
from llm import get_recommendation
from strategy import get_optimal_play

CONCURRENCY = 10


@dataclass
class DecisionRecord:
    hand_id: int
    seed: int
    strategy: str
    decision_num: int
    player_cards: str
    player_value: int
    dealer_upcard: str
    action: str
    optimal_action: str
    result: str | None
    balance_change: float | None


Strategy = Callable[[Game], Awaitable[str]]


async def strategy_optimal(game: Game) -> str:
    return get_optimal_play(game.current_hand, game.dealer_hand)


async def strategy_always_hit(game: Game) -> str:
    return "hit"


async def strategy_always_stand(game: Game) -> str:
    return "stand"


async def strategy_llm(game: Game) -> str:
    rec = await get_recommendation(game)
    return rec.decision if rec else "stand"


STRATEGIES: dict[str, Strategy] = {
    "optimal": strategy_optimal,
    "always_hit": strategy_always_hit,
    "always_stand": strategy_always_stand,
    "llm": strategy_llm,
}


def validate_action(game: Game, action: str) -> str:
    hand = game.current_hand
    if not hand:
        return "stand"

    action = action.lower()
    valid_actions = ["hit", "stand"]

    if hand.can_double:
        valid_actions.append("double")
    if hand.can_split:
        valid_actions.append("split")
    if hand.can_surrender:
        valid_actions.append("surrender")

    if action in valid_actions:
        return action

    return "stand"


def execute_action(game: Game, action: str):
    match action:
        case "hit":
            game.hit()
        case "stand":
            game.stand()
        case "double":
            game.double_down()
        case "split":
            game.split()
        case "surrender":
            game.surrender()


async def play_hand(
    seed: int,
    hand_id: int,
    strategy_name: str,
    strategy_fn: Strategy,
) -> list[DecisionRecord]:
    game = Game(seed=seed)
    game.deal()

    records: list[DecisionRecord] = []
    decision_num = 0

    while game.round_active and game.current_hand:
        player_cards = str(game.current_hand)
        player_value = game.current_hand.value
        dealer_upcard = str(game.dealer_hand.cards[0])

        optimal = get_optimal_play(game.current_hand, game.dealer_hand)
        action = await strategy_fn(game)
        action = validate_action(game, action)

        records.append(
            DecisionRecord(
                hand_id=hand_id,
                seed=seed,
                strategy=strategy_name,
                decision_num=decision_num,
                player_cards=player_cards,
                player_value=player_value,
                dealer_upcard=dealer_upcard,
                action=action,
                optimal_action=optimal,
                result=None,
                balance_change=None,
            )
        )

        execute_action(game, action)
        decision_num += 1

    if game.round_results:
        total_balance = sum(
            get_balance_change(result) * (2.0 if hand.is_doubled else 1.0)
            for hand, result in game.round_results
        )
        result_str = ", ".join(r.value for _, r in game.round_results)

        if records:
            records[-1].result = result_str
            records[-1].balance_change = total_balance
        else:
            records.append(
                DecisionRecord(
                    hand_id=hand_id,
                    seed=seed,
                    strategy=strategy_name,
                    decision_num=0,
                    player_cards=str(game.player_hands[0]),
                    player_value=game.player_hands[0].value,
                    dealer_upcard=str(game.dealer_hand.cards[0]),
                    action="none",
                    optimal_action="none",
                    result=result_str,
                    balance_change=total_balance,
                )
            )

    return records


def get_balance_change(result: HandResult) -> float:
    match result:
        case HandResult.WIN:
            return 1.0
        case HandResult.LOSE:
            return -1.0
        case HandResult.PUSH:
            return 0.0
        case HandResult.BLACKJACK:
            return 1.5
        case HandResult.SURRENDER:
            return -0.5
    return 0.0


async def run_benchmark(
    num_hands: int,
    strategies: list[str],
    start: int = 0,
) -> list[DecisionRecord]:
    semaphore = asyncio.Semaphore(CONCURRENCY)
    completed = 0

    async def play_all_strategies_for_hand(hand_id: int) -> list[DecisionRecord]:
        nonlocal completed
        async with semaphore:
            hand_records: list[DecisionRecord] = []
            for strategy_name in strategies:
                strategy_fn = STRATEGIES[strategy_name]
                records = await play_hand(hand_id, hand_id, strategy_name, strategy_fn)
                hand_records.extend(records)
            completed += 1
            print(f"Completed hand {completed}/{num_hands}")
            return hand_records

    tasks = [
        play_all_strategies_for_hand(hand_id)
        for hand_id in range(start, start + num_hands)
    ]
    results = await asyncio.gather(*tasks)

    all_records: list[DecisionRecord] = []
    for records in results:
        all_records.extend(records)

    return all_records


def save_to_csv(records: list[DecisionRecord], filename: str):
    if not records:
        return

    fieldnames = list(asdict(records[0]).keys())

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def print_summary(records: list[DecisionRecord]):
    strategies = set(r.strategy for r in records)

    print("\n" + "=" * 50)
    print("BENCHMARK SUMMARY")
    print("=" * 50)

    for strategy in sorted(strategies):
        strategy_records = [r for r in records if r.strategy == strategy]
        final_records = [r for r in strategy_records if r.balance_change is not None]

        total_balance = sum(r.balance_change for r in final_records)
        num_hands = len(final_records)

        optimal_matches = sum(
            1 for r in strategy_records if r.action == r.optimal_action
        )
        total_decisions = len(strategy_records)
        accuracy = (optimal_matches / total_decisions * 100) if total_decisions else 0

        print(f"\n{strategy.upper()}")
        print(f"  Hands played: {num_hands}")
        print(f"  Total balance: {total_balance:+.2f}")
        print(f"  Avg per hand: {total_balance / num_hands:+.4f}" if num_hands else "")
        print(
            f"  Decision accuracy: {accuracy:.1f}% ({optimal_matches}/{total_decisions})"
        )


async def main():
    parser = argparse.ArgumentParser(description="Blackjack strategy benchmark")
    parser.add_argument(
        "-n", "--num-hands", type=int, default=10, help="Number of hands to play"
    )
    parser.add_argument("--start", type=int, default=0, help="Starting hand index")
    parser.add_argument(
        "-s",
        "--strategies",
        nargs="+",
        default=["optimal", "always_hit", "always_stand", "llm"],
        choices=list(STRATEGIES.keys()),
        help="Strategies to benchmark",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="benchmark_results.csv",
        help="Output CSV file",
    )
    args = parser.parse_args()

    print(f"Running benchmark with {args.num_hands} hands (starting at {args.start})")
    print(f"Strategies: {', '.join(args.strategies)}")
    print()

    records = await run_benchmark(args.num_hands, args.strategies, args.start)

    save_to_csv(records, args.output)
    print(f"\nResults saved to {args.output}")

    print_summary(records)


if __name__ == "__main__":
    asyncio.run(main())
