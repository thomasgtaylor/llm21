import random
from dataclasses import dataclass, field
from enum import Enum


class Suit(Enum):
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"


class Rank(Enum):
    TWO = ("2", 2)
    THREE = ("3", 3)
    FOUR = ("4", 4)
    FIVE = ("5", 5)
    SIX = ("6", 6)
    SEVEN = ("7", 7)
    EIGHT = ("8", 8)
    NINE = ("9", 9)
    TEN = ("10", 10)
    JACK = ("J", 10)
    QUEEN = ("Q", 10)
    KING = ("K", 10)
    ACE = ("A", 11)

    @property
    def symbol(self) -> str:
        return self.value[0]

    @property
    def points(self) -> int:
        return self.value[1]


@dataclass
class Card:
    rank: Rank
    suit: Suit

    def __str__(self) -> str:
        return f"{self.rank.symbol}{self.suit.value}"

    @property
    def value(self) -> int:
        return self.rank.points


class Shoe:
    def __init__(self, num_decks: int = 6, seed: int | None = None):
        self.num_decks = num_decks
        self.seed = seed
        self.cards: list[Card] = []
        self.reshuffle()

    def reshuffle(self):
        self.cards = [
            Card(rank, suit)
            for _ in range(self.num_decks)
            for suit in Suit
            for rank in Rank
        ]
        if self.seed is not None:
            random.Random(self.seed).shuffle(self.cards)
        else:
            random.shuffle(self.cards)

    def draw(self) -> Card:
        if len(self.cards) < 20:
            self.reshuffle()
        return self.cards.pop()


@dataclass
class Hand:
    cards: list[Card] = field(default_factory=list)
    is_split: bool = False
    is_doubled: bool = False
    is_standing: bool = False
    is_surrendered: bool = False

    def add_card(self, card: Card):
        self.cards.append(card)

    @property
    def value(self) -> int:
        total = sum(card.value for card in self.cards)
        aces = sum(1 for card in self.cards if card.rank == Rank.ACE)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    @property
    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.value == 21 and not self.is_split

    @property
    def is_busted(self) -> bool:
        return self.value > 21

    @property
    def is_split_aces(self) -> bool:
        return self.is_split and len(self.cards) >= 1 and self.cards[0].rank == Rank.ACE

    @property
    def can_split(self) -> bool:
        if len(self.cards) != 2 or self.is_split:
            return False
        return self.cards[0].value == self.cards[1].value

    @property
    def can_double(self) -> bool:
        return len(self.cards) == 2 and not self.is_doubled

    @property
    def can_surrender(self) -> bool:
        return len(self.cards) == 2 and not self.is_split

    @property
    def is_done(self) -> bool:
        return (
            self.is_standing
            or self.is_busted
            or self.is_doubled
            or self.is_split_aces
            or self.is_surrendered
        )

    def __str__(self) -> str:
        return " ".join(str(card) for card in self.cards)


class HandResult(Enum):
    WIN = "win"
    LOSE = "lose"
    PUSH = "push"
    BLACKJACK = "blackjack"
    SURRENDER = "surrender"


@dataclass
class GameStats:
    balance: float = 0.0
    hands_played: int = 0


class Game:
    def __init__(self, num_decks: int = 6, seed: int | None = None):
        self.shoe = Shoe(num_decks, seed=seed)
        self.player_hands: list[Hand] = []
        self.dealer_hand: Hand = Hand()
        self.current_hand_index: int = 0
        self.stats = GameStats()
        self.round_results: list[tuple[Hand, HandResult]] = []
        self.round_active: bool = False

    @property
    def current_hand(self) -> Hand | None:
        if 0 <= self.current_hand_index < len(self.player_hands):
            return self.player_hands[self.current_hand_index]
        return None

    def deal(self):
        self.player_hands = [Hand()]
        self.dealer_hand = Hand()
        self.current_hand_index = 0
        self.round_results = []
        self.round_active = True

        self.player_hands[0].add_card(self.shoe.draw())
        self.dealer_hand.add_card(self.shoe.draw())
        self.player_hands[0].add_card(self.shoe.draw())
        self.dealer_hand.add_card(self.shoe.draw())

        if self.dealer_hand.is_blackjack or self.player_hands[0].is_blackjack:
            self._finish_round()

    def hit(self):
        hand = self.current_hand
        if hand and not hand.is_done:
            hand.add_card(self.shoe.draw())
            if hand.is_busted:
                self._advance_hand()

    def stand(self):
        hand = self.current_hand
        if hand:
            hand.is_standing = True
            self._advance_hand()

    def double_down(self):
        hand = self.current_hand
        if hand and hand.can_double:
            hand.is_doubled = True
            hand.add_card(self.shoe.draw())
            self._advance_hand()

    def split(self):
        hand = self.current_hand
        if hand and hand.can_split:
            is_aces = hand.cards[0].rank == Rank.ACE
            card = hand.cards.pop()
            hand.is_split = True
            new_hand = Hand(cards=[card], is_split=True)
            hand.add_card(self.shoe.draw())
            new_hand.add_card(self.shoe.draw())
            self.player_hands.insert(self.current_hand_index + 1, new_hand)
            if is_aces:
                self.current_hand_index = len(self.player_hands)
                self._finish_round()

    def surrender(self):
        hand = self.current_hand
        if hand and hand.can_surrender:
            hand.is_surrendered = True
            self._advance_hand()

    def _advance_hand(self):
        self.current_hand_index += 1
        if self.current_hand_index >= len(self.player_hands):
            self._finish_round()

    def _finish_round(self):
        self.round_active = False

        while self.dealer_hand.value < 17:
            self.dealer_hand.add_card(self.shoe.draw())

        for hand in self.player_hands:
            result = self._determine_result(hand)
            self.round_results.append((hand, result))
            self._update_stats(hand, result)

    def _determine_result(self, hand: Hand) -> HandResult:
        if hand.is_surrendered:
            return HandResult.SURRENDER
        if hand.is_busted:
            return HandResult.LOSE
        if hand.is_blackjack and self.dealer_hand.is_blackjack:
            return HandResult.PUSH
        if self.dealer_hand.is_blackjack:
            return HandResult.LOSE
        if hand.is_blackjack:
            return HandResult.BLACKJACK
        if self.dealer_hand.is_busted:
            return HandResult.WIN
        if hand.value > self.dealer_hand.value:
            return HandResult.WIN
        if hand.value < self.dealer_hand.value:
            return HandResult.LOSE
        return HandResult.PUSH

    def _update_stats(self, hand: Hand, result: HandResult):
        multiplier = 2.0 if hand.is_doubled else 1.0
        self.stats.hands_played += 1
        match result:
            case HandResult.WIN:
                self.stats.balance += 1.0 * multiplier
            case HandResult.LOSE:
                self.stats.balance -= 1.0 * multiplier
            case HandResult.PUSH:
                pass
            case HandResult.BLACKJACK:
                self.stats.balance += 1.5
            case HandResult.SURRENDER:
                self.stats.balance -= 0.5
