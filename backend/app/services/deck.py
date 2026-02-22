import random
from typing import List
from enum import Enum


class Suit(str, Enum):
    HEARTS = "Hearts"
    DIAMONDS = "Diamonds"
    CLUBS = "Clubs"
    SPADES = "Spades"


class Rank(str, Enum):
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"
    ACE = "A"


class Card:
    def __init__(self, rank: Rank, suit: Suit):
        self.rank = rank
        self.suit = suit

    def value(self) -> int:
        """Returns the base value of the card (Ace = 11 by default)"""
        if self.rank in [Rank.JACK, Rank.QUEEN, Rank.KING]:
            return 10
        elif self.rank == Rank.ACE:
            return 11
        else:
            return int(self.rank.value)

    def __repr__(self):
        return f"{self.rank.value}{self.suit.value[0]}"

    def __str__(self):
        return f"{self.rank.value} of {self.suit.value}"


class Deck:
    def __init__(self):
        self.cards: List[Card] = []
        self.reset()

    def reset(self):
        """Creates a fresh 52-card deck"""
        self.cards = []
        for suit in Suit:
            for rank in Rank:
                self.cards.append(Card(rank, suit))
        self.shuffle()

    def shuffle(self):
        """Shuffles the deck"""
        random.shuffle(self.cards)

    def deal(self) -> Card:
        """Deals one card from the deck"""
        if not self.cards:
            self.reset()
        return self.cards.pop()

    def remaining(self) -> int:
        """Returns number of cards remaining"""
        return len(self.cards)
