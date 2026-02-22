import pytest
from app.services.deck import Deck, Card, Rank, Suit


def test_deck_creation():
    """Test that deck has 52 cards"""
    deck = Deck()
    assert deck.remaining() == 52


def test_deck_deal():
    """Test dealing cards from deck"""
    deck = Deck()
    card = deck.deal()
    assert isinstance(card, Card)
    assert deck.remaining() == 51


def test_deck_reset():
    """Test deck reset and shuffle"""
    deck = Deck()
    # Deal some cards
    for _ in range(10):
        deck.deal()
    assert deck.remaining() == 42
    
    # Reset
    deck.reset()
    assert deck.remaining() == 52


def test_card_values():
    """Test card value calculation"""
    assert Card(Rank.TWO, Suit.HEARTS).value() == 2
    assert Card(Rank.TEN, Suit.SPADES).value() == 10
    assert Card(Rank.JACK, Suit.CLUBS).value() == 10
    assert Card(Rank.QUEEN, Suit.DIAMONDS).value() == 10
    assert Card(Rank.KING, Suit.HEARTS).value() == 10
    assert Card(Rank.ACE, Suit.SPADES).value() == 11
