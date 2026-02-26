from typing import List, Set, Tuple
from decimal import Decimal
import logging

from app.services.deck import Card, Deck, Rank

logger = logging.getLogger(__name__)


class Hand:
    def __init__(self):
        self.cards: List[Card] = []

    def add_card(self, card: Card):
        """Add a card to the hand"""
        self.cards.append(card)

    def value(self) -> int:
        """
        Calculate the best value of the hand.
        Handles Ace as 11 or 1 intelligently.
        """
        total = 0
        aces = 0

        for card in self.cards:
            if card.rank == Rank.ACE:
                aces += 1
                total += 11
            else:
                total += card.value()

        # Adjust for aces if busted
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1

        return total

    def is_blackjack(self) -> bool:
        """Check if hand is a natural blackjack (21 with 2 cards)"""
        return len(self.cards) == 2 and self.value() == 21

    def is_bust(self) -> bool:
        """Check if hand is busted"""
        return self.value() > 21

    def is_soft(self) -> bool:
        """
        Return True if at least one ace is currently counted as 11.
        Computes the 'hard' value (all aces = 1) and compares it to the
        optimal value(); any difference means an ace is still being used as 11.
        """
        if not any(card.rank == Rank.ACE for card in self.cards):
            return False
        hard_value = sum(1 if c.rank == Rank.ACE else c.value() for c in self.cards)
        return hard_value != self.value()

    def __repr__(self):
        return f"Hand({[str(card) for card in self.cards]}, value={self.value()})"


class GameEngine:
    """
    Core Blackjack game engine.
    Handles all game logic in isolation from API/database concerns.

    Phase 1: Added double-down support (can_double_down, player_double_down).
    Phase 2: Refactored to multi-hand support for split (player_hands list).
             player_hand remains as a backward-compat property pointing to the
             current active hand.
    """

    def __init__(self):
        self.deck = Deck()
        # Phase 2: multi-hand list; single hand by default for backward compat
        self.player_hands: List[Hand] = [Hand()]
        # Tracks wager per player hand (set by API layer when a game starts).
        self.hand_bets: List[Decimal] = []
        self.current_hand_index: int = 0
        self.dealer_hand = Hand()
        self.game_over = False
        # Phase 2 split flags
        self.is_split: bool = False
        self.split_aces: bool = False  # True when split was performed on Aces
        self._stood_hands: Set[int] = set()  # Tracks which hand indices have been stood

    # ------------------------------------------------------------------
    # Backward-compat property
    # ------------------------------------------------------------------

    @property
    def player_hand(self) -> Hand:
        """Returns the currently active hand (backward-compatible access)."""
        return self.player_hands[self.current_hand_index]

    # ------------------------------------------------------------------
    # Core deal
    # ------------------------------------------------------------------

    def deal_initial_cards(self):
        """Deal initial two cards each to player and dealer"""
        self.player_hand.add_card(self.deck.deal())
        self.dealer_hand.add_card(self.deck.deal())
        self.player_hand.add_card(self.deck.deal())
        self.dealer_hand.add_card(self.deck.deal())

        logger.info(
            f"Initial deal - Player: {self.player_hand.value()}, "
            f"Dealer showing: {self.dealer_hand.cards[0]}"
        )

    # ------------------------------------------------------------------
    # Phase 1: Double Down
    # ------------------------------------------------------------------

    def can_double_down(self) -> bool:
        """
        True when the current active hand has exactly 2 cards and game is active.
        House rule: double-down is only allowed on the original (non-split) hand.
        """
        return (
            len(self.player_hand.cards) == 2
            and not self.game_over
            and not self.is_split
        )

    def player_double_down(self) -> Card:
        """
        Double down: deal exactly one card to the current hand,
        then immediately trigger dealer play and mark game over.
        Returns the single dealt card.
        """
        card = self.deck.deal()
        self.player_hand.add_card(card)
        self.dealer_play()
        self.game_over = True
        logger.info(
            f"Player doubled down on hand {self.current_hand_index}: "
            f"{card}, hand value: {self.player_hand.value()}"
        )
        return card

    # ------------------------------------------------------------------
    # Player actions
    # ------------------------------------------------------------------

    def player_hit(self) -> Card:
        """Deal one card to the current active hand."""
        card = self.deck.deal()
        self.player_hand.add_card(card)
        logger.info(
            f"Player hit on hand {self.current_hand_index}: "
            f"{card}, hand value: {self.player_hand.value()}"
        )
        return card

    def player_stand(self) -> str:
        """
        Player stands on current hand.
        - If more hands remain, advance current_hand_index and return 'next_hand'.
        - If this was the last hand, return 'done' (caller triggers dealer play).
        """
        self._stood_hands.add(self.current_hand_index)

        if self.current_hand_index < len(self.player_hands) - 1:
            self.current_hand_index += 1
            logger.info(f"Stand: advancing to hand {self.current_hand_index}")
            return "next_hand"

        logger.info("Stand: last hand — dealer play required by caller")
        return "done"

    def dealer_play(self):
        """
        Dealer plays according to standard rules:
        - Must hit until reaching 17 or higher.
        - Stands on soft 17.
        """
        logger.info(f"Dealer starts with: {self.dealer_hand.value()}")

        while self.dealer_hand.value() < 17:
            card = self.deck.deal()
            self.dealer_hand.add_card(card)
            logger.info(f"Dealer hit: {card}, hand value: {self.dealer_hand.value()}")

        logger.info(f"Dealer stands at: {self.dealer_hand.value()}")

    # ------------------------------------------------------------------
    # Phase 2: Split
    # ------------------------------------------------------------------

    def can_split(self) -> bool:
        """
        True when:
        - Only one hand exists (not already split)
        - That hand has exactly 2 cards of the same rank
        - Game is still active
        """
        if self.is_split or self.game_over:
            return False
        hand = self.player_hands[0]
        return (
            len(self.player_hands) == 1
            and len(hand.cards) == 2
            and hand.cards[0].rank == hand.cards[1].rank
        )

    def player_split(self) -> Tuple[Card, Card]:
        """
        Split the current hand into two independent hands.
        Each hand starts with the original card plus one newly dealt card.

        Returns the two dealt cards (card for hand 0, card for hand 1).
        Sets self.split_aces = True if the split was performed on Aces,
        which means no further hitting is allowed on either hand.
        """
        if not self.can_split():
            raise ValueError("Cannot split: conditions not met")

        original_hand = self.player_hands[0]
        split_rank = original_hand.cards[0].rank

        # Move the second card out to form the new hand
        second_card = original_hand.cards.pop(1)
        new_hand = Hand()
        new_hand.add_card(second_card)
        self.player_hands.append(new_hand)

        # Deal one card to each hand
        card1 = self.deck.deal()
        original_hand.add_card(card1)

        card2 = self.deck.deal()
        new_hand.add_card(card2)

        self.is_split = True
        self.current_hand_index = 0

        # Split aces rule: no further hitting on either hand
        if split_rank == Rank.ACE:
            self.split_aces = True
            logger.info(
                "Split aces detected — both hands auto-stand after one card each"
            )

        logger.info(f"Split complete. Hand 0: {original_hand}, Hand 1: {new_hand}")
        return card1, card2

    # ------------------------------------------------------------------
    # Winner determination
    # ------------------------------------------------------------------

    def determine_winner(self) -> List[Tuple[str, float]]:
        """
        Determine the outcome for every player hand.
        Returns a list of (result, multiplier) tuples — one entry per hand.

        Non-split games return a single-element list for backward compat.

        Multipliers:
          2.5 — blackjack (natural only; split 21 pays 1:1 per standard rules)
          2.0 — win
          1.0 — push
          0.0 — lose
        """
        results: List[Tuple[str, float]] = []
        dealer_value = self.dealer_hand.value()
        dealer_bust = self.dealer_hand.is_bust()
        dealer_blackjack = self.dealer_hand.is_blackjack()

        for hand in self.player_hands:
            player_value = hand.value()
            player_bust = hand.is_bust()
            # Natural blackjack (3:2) only counts on un-split hands
            player_blackjack = hand.is_blackjack() and not self.is_split

            if player_bust:
                logger.info("Hand busts — lose")
                results.append(("lose", 0.0))
            elif player_blackjack and not dealer_blackjack:
                logger.info("Player blackjack!")
                results.append(("blackjack", 2.5))
            elif player_blackjack and dealer_blackjack:
                logger.info("Both blackjack — push")
                results.append(("push", 1.0))
            elif dealer_bust:
                logger.info("Dealer busts — player wins")
                results.append(("win", 2.0))
            elif player_value > dealer_value:
                logger.info(f"Player wins: {player_value} vs {dealer_value}")
                results.append(("win", 2.0))
            elif player_value < dealer_value:
                logger.info(f"Dealer wins: {dealer_value} vs {player_value}")
                results.append(("lose", 0.0))
            else:
                logger.info(f"Push: both {player_value}")
                results.append(("push", 1.0))

        return results

    # ------------------------------------------------------------------
    # State snapshot
    # ------------------------------------------------------------------

    def get_game_state(self) -> dict:
        """
        Return a full snapshot of the current game state.
        Includes backward-compat keys (player_hand, player_value) alongside
        the new split-aware player_hands list.
        """
        hand_states = []
        for i, hand in enumerate(self.player_hands):
            # Compute per-hand status label
            if hand.is_bust():
                status = "bust"
            elif hand.is_blackjack() and not self.is_split:
                status = "blackjack"
            elif i in self._stood_hands:
                status = "stood"
            else:
                status = "active"

            hand_states.append(
                {
                    "cards": [
                        {"rank": c.rank.value, "suit": c.suit.value} for c in hand.cards
                    ],
                    "value": hand.value(),
                    "status": status,
                    # Double-down eligible only for the current hand with 2 cards
                    "can_double_down": (
                        len(hand.cards) == 2
                        and i == self.current_hand_index
                        and not self.game_over
                    ),
                }
            )

        current_hand = self.player_hand
        return {
            # --- backward-compat keys ---
            "player_hand": [
                {"rank": c.rank.value, "suit": c.suit.value} for c in current_hand.cards
            ],
            "player_value": current_hand.value(),
            "dealer_hand": [
                {"rank": c.rank.value, "suit": c.suit.value}
                for c in self.dealer_hand.cards
            ],
            "dealer_value": self.dealer_hand.value(),
            "player_bust": current_hand.is_bust(),
            "dealer_bust": self.dealer_hand.is_bust(),
            "player_blackjack": current_hand.is_blackjack(),
            "game_over": self.game_over,
            # --- Phase 1 ---
            "can_double_down": self.can_double_down(),
            # --- Phase 2 ---
            "is_split": self.is_split,
            "can_split": self.can_split(),
            "player_hands": hand_states,
            "current_hand_index": self.current_hand_index,
        }
