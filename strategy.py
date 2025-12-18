from blackjack import Hand, Rank

HARD_STRATEGY = {
    21: "SSSSSSSSSS",
    20: "SSSSSSSSSS",
    19: "SSSSSSSSSS",
    18: "SSSSSSSSSS",
    17: "SSSSSSSSSS",
    16: "SSSSSHHRRR",
    15: "SSSSSHHHRH",
    14: "SSSSSHHHHH",
    13: "SSSSSHHHHH",
    12: "HHSSSHHHHH",
    11: "DDDDDDDDDD",
    10: "DDDDDDDDHH",
    9: "HDDDDHHHHH",
    8: "HHHHHHHHHH",
    7: "HHHHHHHHHH",
    6: "HHHHHHHHHH",
    5: "HHHHHHHHHH",
}

SOFT_STRATEGY = {
    21: "SSSSSSSSSS",
    20: "SSSSSSSSSS",
    19: "SSSSSSSSSS",
    18: "SDDDDSSHHH",
    17: "HDDDDHHHHH",
    16: "HHDDDHHHHH",
    15: "HHDDDHHHHH",
    14: "HHHDDHHHHH",
    13: "HHHDDHHHHH",
}

PAIR_STRATEGY = {
    Rank.ACE: "PPPPPPPPPP",
    Rank.TEN: "SSSSSSSSSS",
    Rank.NINE: "PPPPPSPPSS",
    Rank.EIGHT: "PPPPPPPPPP",
    Rank.SEVEN: "PPPPPPHHHH",
    Rank.SIX: "PPPPPHHHHH",
    Rank.FIVE: "DDDDDDDDHH",
    Rank.FOUR: "HHHPPHHHHH",
    Rank.THREE: "PPPPPPHHHH",
    Rank.TWO: "PPPPPPHHHH",
}

DEALER_INDEX = {2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 7, 10: 8, 11: 9}

ACTION_MAP = {
    "S": "stand",
    "H": "hit",
    "D": "double",
    "P": "split",
    "R": "surrender",
}


def get_dealer_value(hand: Hand) -> int:
    card = hand.cards[0]
    if card.rank == Rank.ACE:
        return 11
    return card.value


def is_soft(hand: Hand) -> bool:
    total = sum(card.value for card in hand.cards)
    aces = sum(1 for card in hand.cards if card.rank == Rank.ACE)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    has_active_ace = any(card.rank == Rank.ACE for card in hand.cards) and total <= 21
    base_total = sum(1 if card.rank == Rank.ACE else card.value for card in hand.cards)
    return has_active_ace and base_total + 10 <= 21


def is_pair(hand: Hand) -> bool:
    return len(hand.cards) == 2 and hand.cards[0].value == hand.cards[1].value


def get_optimal_play(player_hand: Hand, dealer_hand: Hand) -> str:
    dealer_val = get_dealer_value(dealer_hand)
    dealer_idx = DEALER_INDEX.get(dealer_val, 9)

    if is_pair(player_hand) and not player_hand.is_split:
        rank = player_hand.cards[0].rank
        if rank in (Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING):
            rank = Rank.TEN
        if rank in PAIR_STRATEGY:
            action = PAIR_STRATEGY[rank][dealer_idx]
            return ACTION_MAP[action]

    if is_soft(player_hand):
        value = player_hand.value
        if value in SOFT_STRATEGY:
            action = SOFT_STRATEGY[value][dealer_idx]
            if action == "D" and not player_hand.can_double:
                action = "H" if value <= 17 else "S"
            return ACTION_MAP.get(action, action)

    value = player_hand.value
    if value in HARD_STRATEGY:
        action = HARD_STRATEGY[value][dealer_idx]
        if action == "D" and not player_hand.can_double:
            action = "H"
        if action == "R" and not player_hand.can_surrender:
            action = "H"
        return ACTION_MAP.get(action, action)

    if value >= 17:
        return "stand"
    return "hit"


def evaluate_decision(player_hand: Hand, dealer_hand: Hand, decision: str) -> bool:
    optimal = get_optimal_play(player_hand, dealer_hand)
    return decision.lower() == optimal.lower()
