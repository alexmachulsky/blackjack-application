"""
test_game_engine.py

Unit tests for GameEngine and Hand.

determine_winner() now returns List[Tuple[str, float]] (one entry per hand).
Existing tests use results[0] to unpack — this keeps them backward-compatible
with the Phase 2 multi-hand refactor while preserving all original assertions.
"""

import pytest
from app.services.game_engine import GameEngine, Hand
from app.services.deck import Card, Rank, Suit

pytestmark = pytest.mark.unit


# ===========================================================================
# Hand tests (unchanged behaviour)
# ===========================================================================


def test_hand_value_simple():
    """Test simple hand value calculation"""
    hand = Hand()
    hand.add_card(Card(Rank.FIVE, Suit.HEARTS))
    hand.add_card(Card(Rank.TEN, Suit.SPADES))
    assert hand.value() == 15


def test_hand_value_with_ace_soft():
    """Test hand with ace (soft hand)"""
    hand = Hand()
    hand.add_card(Card(Rank.ACE, Suit.HEARTS))
    hand.add_card(Card(Rank.SIX, Suit.SPADES))
    assert hand.value() == 17
    assert hand.is_soft()


def test_hand_value_with_ace_hard():
    """Test hand with ace counted as 1"""
    hand = Hand()
    hand.add_card(Card(Rank.ACE, Suit.HEARTS))
    hand.add_card(Card(Rank.FIVE, Suit.SPADES))
    hand.add_card(Card(Rank.TEN, Suit.CLUBS))
    assert hand.value() == 16  # Ace counts as 1


def test_hand_value_multiple_aces():
    """Test hand with multiple aces"""
    hand = Hand()
    hand.add_card(Card(Rank.ACE, Suit.HEARTS))
    hand.add_card(Card(Rank.ACE, Suit.SPADES))
    assert hand.value() == 12  # One ace as 11, one as 1


def test_hand_blackjack():
    """Test blackjack detection"""
    hand = Hand()
    hand.add_card(Card(Rank.ACE, Suit.HEARTS))
    hand.add_card(Card(Rank.KING, Suit.SPADES))
    assert hand.is_blackjack()
    assert hand.value() == 21


def test_hand_blackjack_false():
    """Test non-blackjack 21"""
    hand = Hand()
    hand.add_card(Card(Rank.FIVE, Suit.HEARTS))
    hand.add_card(Card(Rank.SIX, Suit.SPADES))
    hand.add_card(Card(Rank.TEN, Suit.CLUBS))
    assert hand.value() == 21
    assert not hand.is_blackjack()


def test_hand_bust():
    """Test bust detection"""
    hand = Hand()
    hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    hand.add_card(Card(Rank.KING, Suit.SPADES))
    hand.add_card(Card(Rank.FIVE, Suit.CLUBS))
    assert hand.is_bust()
    assert hand.value() == 25


# ===========================================================================
# GameEngine core tests (updated to use results[0] for new return type)
# ===========================================================================


def test_game_engine_initial_deal():
    """Test initial card deal"""
    engine = GameEngine()
    engine.deal_initial_cards()
    # player_hand is a backward-compat property
    assert len(engine.player_hand.cards) == 2
    assert len(engine.dealer_hand.cards) == 2


def test_game_engine_player_hit():
    """Test player hitting"""
    engine = GameEngine()
    engine.deal_initial_cards()

    initial_count = len(engine.player_hand.cards)
    engine.player_hit()

    assert len(engine.player_hand.cards) == initial_count + 1


def test_game_engine_dealer_play():
    """Test dealer play logic"""
    engine = GameEngine()
    engine.dealer_hand.add_card(Card(Rank.TWO, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.THREE, Suit.SPADES))

    engine.dealer_play()

    assert engine.dealer_hand.value() >= 17 or engine.dealer_hand.is_bust()


def test_determine_winner_player_bust():
    """Test player bust scenario"""
    engine = GameEngine()
    engine.player_hand.add_card(Card(Rank.KING, Suit.HEARTS))
    engine.player_hand.add_card(Card(Rank.QUEEN, Suit.SPADES))
    engine.player_hand.add_card(Card(Rank.FIVE, Suit.CLUBS))

    engine.dealer_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.SEVEN, Suit.SPADES))

    result, multiplier = engine.determine_winner()[0]
    assert result == "lose"
    assert multiplier == 0.0


def test_determine_winner_player_blackjack():
    """Test player blackjack"""
    engine = GameEngine()
    engine.player_hand.add_card(Card(Rank.ACE, Suit.HEARTS))
    engine.player_hand.add_card(Card(Rank.KING, Suit.SPADES))

    engine.dealer_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.SEVEN, Suit.SPADES))

    result, multiplier = engine.determine_winner()[0]
    assert result == "blackjack"
    assert multiplier == 2.5


def test_determine_winner_dealer_bust():
    """Test dealer bust"""
    engine = GameEngine()
    engine.player_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.player_hand.add_card(Card(Rank.EIGHT, Suit.SPADES))

    engine.dealer_hand.add_card(Card(Rank.KING, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.QUEEN, Suit.SPADES))
    engine.dealer_hand.add_card(Card(Rank.FIVE, Suit.CLUBS))

    result, multiplier = engine.determine_winner()[0]
    assert result == "win"
    assert multiplier == 2.0


def test_determine_winner_push():
    """Test push scenario"""
    engine = GameEngine()
    engine.player_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.player_hand.add_card(Card(Rank.NINE, Suit.SPADES))

    engine.dealer_hand.add_card(Card(Rank.KING, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.NINE, Suit.CLUBS))

    result, multiplier = engine.determine_winner()[0]
    assert result == "push"
    assert multiplier == 1.0


def test_determine_winner_player_wins():
    """Test player wins with higher value"""
    engine = GameEngine()
    engine.player_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.player_hand.add_card(Card(Rank.TEN, Suit.SPADES))

    engine.dealer_hand.add_card(Card(Rank.TEN, Suit.CLUBS))
    engine.dealer_hand.add_card(Card(Rank.EIGHT, Suit.DIAMONDS))

    result, multiplier = engine.determine_winner()[0]
    assert result == "win"
    assert multiplier == 2.0


# ===========================================================================
# Phase 1: Double Down tests
# ===========================================================================


def test_can_double_down_initial_deal():
    """should return True when player has exactly 2 cards after initial deal"""
    engine = GameEngine()
    engine.deal_initial_cards()
    assert engine.can_double_down() is True


def test_can_double_down_after_hit():
    """should return False when player has hit (hand has more than 2 cards)"""
    engine = GameEngine()
    engine.deal_initial_cards()
    engine.player_hit()
    assert engine.can_double_down() is False


def test_can_double_down_game_over():
    """should return False when game_over flag is True"""
    engine = GameEngine()
    engine.deal_initial_cards()
    engine.game_over = True
    assert engine.can_double_down() is False


def test_player_double_down_deals_one_card():
    """should result in player hand having exactly 3 cards after double down"""
    engine = GameEngine()
    engine.deal_initial_cards()
    engine.player_double_down()
    assert len(engine.player_hand.cards) == 3


def test_player_double_down_triggers_dealer():
    """should cause dealer to play (hand >= 17 or bust) after double down"""
    engine = GameEngine()
    engine.deal_initial_cards()
    engine.player_double_down()
    assert engine.dealer_hand.value() >= 17 or engine.dealer_hand.is_bust()


def test_player_double_down_sets_game_over():
    """should set game_over to True after double down"""
    engine = GameEngine()
    engine.deal_initial_cards()
    engine.player_double_down()
    assert engine.game_over is True


def test_double_down_payout_calculation():
    """should return correct win multiplier on a winning 3-card double-down hand"""
    engine = GameEngine()
    # Set up a winning 3-card hand: 7 + 7 + 7 = 21
    engine.player_hand.add_card(Card(Rank.SEVEN, Suit.HEARTS))
    engine.player_hand.add_card(Card(Rank.SEVEN, Suit.SPADES))
    engine.player_hand.add_card(Card(Rank.SEVEN, Suit.CLUBS))  # 3-card 21

    engine.dealer_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.EIGHT, Suit.SPADES))  # dealer 18

    result, multiplier = engine.determine_winner()[0]
    assert result == "win"
    assert multiplier == 2.0


# ===========================================================================
# Phase 2: Split tests
# ===========================================================================


def test_can_split_matching_ranks():
    """should return True when player has two cards of the same rank"""
    engine = GameEngine()
    engine.player_hand.add_card(Card(Rank.EIGHT, Suit.HEARTS))
    engine.player_hand.add_card(Card(Rank.EIGHT, Suit.SPADES))
    engine.dealer_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.SIX, Suit.SPADES))
    assert engine.can_split() is True


def test_can_split_different_ranks():
    """should return False when player cards have different ranks"""
    engine = GameEngine()
    engine.player_hand.add_card(Card(Rank.EIGHT, Suit.HEARTS))
    engine.player_hand.add_card(Card(Rank.NINE, Suit.SPADES))
    assert engine.can_split() is False


def test_can_split_after_hit():
    """should return False when player has more than 2 cards"""
    engine = GameEngine()
    engine.player_hand.add_card(Card(Rank.EIGHT, Suit.HEARTS))
    engine.player_hand.add_card(Card(Rank.EIGHT, Suit.SPADES))
    engine.player_hand.add_card(Card(Rank.TWO, Suit.CLUBS))  # extra hit card
    assert engine.can_split() is False


def test_player_split_creates_two_hands():
    """should result in exactly 2 hands, each with 2 cards, after a split"""
    engine = GameEngine()
    # Give player a pair of 8s
    engine.player_hands[0].add_card(Card(Rank.EIGHT, Suit.HEARTS))
    engine.player_hands[0].add_card(Card(Rank.EIGHT, Suit.SPADES))
    engine.dealer_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.SIX, Suit.SPADES))

    engine.player_split()

    assert len(engine.player_hands) == 2
    assert len(engine.player_hands[0].cards) == 2
    assert len(engine.player_hands[1].cards) == 2


def test_split_hit_applies_to_current_hand():
    """should only add a card to the currently active hand (hand 0) after a split"""
    engine = GameEngine()
    engine.player_hands[0].add_card(Card(Rank.EIGHT, Suit.HEARTS))
    engine.player_hands[0].add_card(Card(Rank.EIGHT, Suit.SPADES))
    engine.dealer_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.SIX, Suit.SPADES))

    engine.player_split()
    pre_split_h1_count = len(engine.player_hands[1].cards)

    engine.player_hit()  # hits hand 0

    assert len(engine.player_hands[0].cards) == 3
    assert len(engine.player_hands[1].cards) == pre_split_h1_count  # hand 1 unchanged


def test_split_stand_advances_hand():
    """should advance current_hand_index to 1 and return 'next_hand' when standing on hand 0"""
    engine = GameEngine()
    engine.player_hands[0].add_card(Card(Rank.EIGHT, Suit.HEARTS))
    engine.player_hands[0].add_card(Card(Rank.EIGHT, Suit.SPADES))
    engine.dealer_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.SIX, Suit.SPADES))

    engine.player_split()
    result = engine.player_stand()  # stand on hand 0

    assert result == "next_hand"
    assert engine.current_hand_index == 1


def test_split_stand_last_hand_triggers_dealer():
    """should return 'done' (signalling caller to trigger dealer) when standing on final hand"""
    engine = GameEngine()
    engine.player_hands[0].add_card(Card(Rank.EIGHT, Suit.HEARTS))
    engine.player_hands[0].add_card(Card(Rank.EIGHT, Suit.SPADES))
    engine.dealer_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.SIX, Suit.SPADES))

    engine.player_split()
    engine.player_stand()  # advance to hand 1
    result = engine.player_stand()  # stand on hand 1 (the last)

    assert result == "done"


def test_split_aces_auto_stand():
    """should set split_aces=True and each hand gets exactly 2 cards when splitting aces"""
    engine = GameEngine()
    engine.player_hands[0].add_card(Card(Rank.ACE, Suit.HEARTS))
    engine.player_hands[0].add_card(Card(Rank.ACE, Suit.SPADES))
    engine.dealer_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.SIX, Suit.SPADES))

    engine.player_split()

    assert engine.split_aces is True
    assert len(engine.player_hands[0].cards) == 2
    assert len(engine.player_hands[1].cards) == 2


def test_split_determine_winner_multiple_results():
    """should return a list with one result tuple per hand after a split"""
    engine = GameEngine()
    engine.player_hands[0].add_card(Card(Rank.EIGHT, Suit.HEARTS))
    engine.player_hands[0].add_card(Card(Rank.EIGHT, Suit.SPADES))
    engine.dealer_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.SIX, Suit.SPADES))

    engine.player_split()
    results = engine.determine_winner()

    assert len(results) == 2
    for result, multiplier in results:
        assert result in ("win", "lose", "push", "blackjack")
        assert multiplier in (0.0, 1.0, 2.0, 2.5)


def test_split_double_down_on_split_hand():
    """double down is not allowed after split under current house rules"""
    engine = GameEngine()
    engine.player_hands[0].add_card(Card(Rank.EIGHT, Suit.HEARTS))
    engine.player_hands[0].add_card(Card(Rank.EIGHT, Suit.SPADES))
    engine.dealer_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.SIX, Suit.SPADES))

    engine.player_split()

    # After split each hand has exactly 2 cards, but double-down remains disabled
    assert engine.can_double_down() is False


def test_split_both_bust():
    """should correctly report both hands as losses when both bust"""
    engine = GameEngine()
    # Manually build two busted hands
    engine.player_hands[0].add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.player_hands[0].add_card(Card(Rank.TEN, Suit.SPADES))
    engine.player_hands[0].add_card(Card(Rank.FIVE, Suit.CLUBS))  # bust: 25

    bust_hand = Hand()
    bust_hand.add_card(Card(Rank.KING, Suit.HEARTS))
    bust_hand.add_card(Card(Rank.QUEEN, Suit.SPADES))
    bust_hand.add_card(Card(Rank.FOUR, Suit.CLUBS))  # bust: 24
    engine.player_hands.append(bust_hand)
    engine.is_split = True

    engine.dealer_hand.add_card(Card(Rank.TEN, Suit.HEARTS))
    engine.dealer_hand.add_card(Card(Rank.SEVEN, Suit.SPADES))

    results = engine.determine_winner()
    assert len(results) == 2
    assert all(r == "lose" for r, _ in results)
    assert all(m == 0.0 for _, m in results)
