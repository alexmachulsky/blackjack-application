# PLAN.md

## Feature
Double Down

## User Story
As a player, I want to double my bet after the initial deal and receive exactly one more card, so that I can maximize winnings on strong starting hands.

## Branch
`feature/double-down`

## Steps
1. Add `can_double_down()` and `player_double_down()` methods to `GameEngine`
2. Add `can_double_down` field to `GameState` schema
3. Add `POST /game/double-down` route
4. Update existing `start_game`, `hit`, `stand`, `_finish_game` returns to pass `can_double_down` into `GameState`
5. Add `doubleDown()` function to frontend API client
6. Add Double Down button + handler to `GamePage.jsx`
7. Add unit tests for double-down engine logic
8. Run all tests and verify nothing is broken

## Files to Create or Modify
- `backend/app/services/game_engine.py` → add `can_double_down()`, `player_double_down()`, update `get_game_state()`
- `backend/app/schemas/game.py` → add `can_double_down: bool = False` to `GameState`
- `backend/app/routes/game.py` → add `POST /double-down` endpoint; update `start_game`, `hit`, `stand`, `_finish_game` to pass `can_double_down`
- `frontend/src/services/api.js` → add `doubleDown()` export
- `frontend/src/pages/GamePage.jsx` → add `handleDoubleDown` handler + conditional button
- `backend/tests/test_game_engine.py` → add 7 new tests

## Edge Cases
- **Insufficient balance:** Player's remaining balance is less than the original bet → return 400 `"Insufficient balance to double down"`
- **Already hit:** Player has more than 2 cards (already hit once) → return 400 `"Double down only available on initial hand"`
- **Game already over:** Game status is not `"active"` → return 400 `"Game is not active"` (existing guard)
- **Player busts after double down:** Hand exceeds 21 after the single card → game ends as a loss on the doubled bet

## Acceptance Criteria
- [ ] Double Down button appears only when player has exactly 2 cards and game is active
- [ ] Button is hidden/disabled if user's balance < original bet amount
- [ ] Clicking Double Down deducts an additional bet equal to the original from balance
- [ ] Player receives exactly 1 card, then dealer auto-plays and game resolves
- [ ] Payout is calculated on the doubled bet amount (e.g., $10 bet → $20 doubled → $40 win)
- [ ] Double Down is no longer available after player hits
- [ ] All 11 existing engine tests still pass
- [ ] At least 7 new unit tests pass covering double-down logic

## Commit Message
`feat(game): add double down action with bet doubling and auto-resolve`