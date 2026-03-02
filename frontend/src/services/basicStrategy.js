/**
 * basicStrategy.js — Standard basic strategy chart for 4–8 deck blackjack.
 *
 * Rules assumed: Dealer stands on soft 17, double after split allowed,
 * blackjack pays 3:2, no surrender.
 *
 * Returns one of: 'H' (hit), 'S' (stand), 'D' (double), 'P' (split)
 */

// Map card rank → numeric value for lookup (face cards = 10, Ace = 11)
function cardValue(rank) {
  if (rank === 'A') return 11;
  if (['K', 'Q', 'J'].includes(rank)) return 10;
  return parseInt(rank, 10) || 0;
}

/**
 * Compute hand total & softness from an array of { rank, suit } cards.
 */
function handInfo(cards) {
  let total = 0;
  let aces = 0;
  for (const c of cards) {
    const v = cardValue(c.rank);
    total += v;
    if (c.rank === 'A') aces++;
  }
  while (total > 21 && aces > 0) {
    total -= 10;
    aces--;
  }
  return { total, soft: aces > 0, count: cards.length };
}

// ── Hard totals chart ────────────────────────────────────────────────────
// Rows: player hard total (5–20). Columns: dealer upcard (2–11, where 11=Ace).
// H=hit, S=stand, D=double (hit if can't), Dh=double else hit, Ds=double else stand
const HARD = {
  //         2    3    4    5    6    7    8    9    10   A
  5:       ['H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H'],
  6:       ['H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H'],
  7:       ['H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H'],
  8:       ['H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H'],
  9:       ['H', 'D', 'D', 'D', 'D', 'H', 'H', 'H', 'H', 'H'],
  10:      ['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'H', 'H'],
  11:      ['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'D'],
  12:      ['H', 'H', 'S', 'S', 'S', 'H', 'H', 'H', 'H', 'H'],
  13:      ['S', 'S', 'S', 'S', 'S', 'H', 'H', 'H', 'H', 'H'],
  14:      ['S', 'S', 'S', 'S', 'S', 'H', 'H', 'H', 'H', 'H'],
  15:      ['S', 'S', 'S', 'S', 'S', 'H', 'H', 'H', 'H', 'H'],
  16:      ['S', 'S', 'S', 'S', 'S', 'H', 'H', 'H', 'H', 'H'],
  17:      ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S'],
  18:      ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S'],
  19:      ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S'],
  20:      ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S'],
};

// ── Soft totals chart ────────────────────────────────────────────────────
// Rows: player soft total (13–20). Columns: dealer upcard (2–11).
const SOFT = {
  //         2    3    4    5    6    7    8    9    10   A
  13:      ['H', 'H', 'H', 'D', 'D', 'H', 'H', 'H', 'H', 'H'],
  14:      ['H', 'H', 'H', 'D', 'D', 'H', 'H', 'H', 'H', 'H'],
  15:      ['H', 'H', 'D', 'D', 'D', 'H', 'H', 'H', 'H', 'H'],
  16:      ['H', 'H', 'D', 'D', 'D', 'H', 'H', 'H', 'H', 'H'],
  17:      ['H', 'D', 'D', 'D', 'D', 'H', 'H', 'H', 'H', 'H'],
  18:      ['D', 'D', 'D', 'D', 'D', 'S', 'S', 'H', 'H', 'H'],
  19:      ['S', 'S', 'S', 'S', 'D', 'S', 'S', 'S', 'S', 'S'],
  20:      ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S'],
};

// ── Pair splitting chart ─────────────────────────────────────────────────
// Rows: pair card value (2–11, where 11=Ace). Columns: dealer upcard (2–11).
// Y=split, N=don't split, D=split if double after split allowed (we allow it)
const PAIR = {
  //         2    3    4    5    6    7    8    9    10   A
  2:       ['P', 'P', 'P', 'P', 'P', 'P', 'H', 'H', 'H', 'H'],
  3:       ['P', 'P', 'P', 'P', 'P', 'P', 'H', 'H', 'H', 'H'],
  4:       ['H', 'H', 'H', 'P', 'P', 'H', 'H', 'H', 'H', 'H'],
  5:       ['D', 'D', 'D', 'D', 'D', 'D', 'D', 'D', 'H', 'H'],
  6:       ['P', 'P', 'P', 'P', 'P', 'H', 'H', 'H', 'H', 'H'],
  7:       ['P', 'P', 'P', 'P', 'P', 'P', 'H', 'H', 'H', 'H'],
  8:       ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
  9:       ['P', 'P', 'P', 'P', 'P', 'S', 'P', 'P', 'S', 'S'],
  10:      ['S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S', 'S'],
  11:      ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'], // Aces
};

/**
 * Dealer upcard index (0–9) from a dealer card rank.
 * 2→0, 3→1, …, 10→8, A→9
 */
function dealerIndex(rank) {
  if (rank === 'A') return 9;
  const v = cardValue(rank);
  return Math.max(0, Math.min(8, v - 2));
}

/**
 * Look up the basic strategy recommendation.
 *
 * @param {Array<{rank:string, suit:string}>} playerCards - player's hand
 * @param {{rank:string, suit:string}} dealerUpcard - dealer's visible card
 * @param {boolean} canDouble - whether doubling is allowed right now
 * @param {boolean} canSplit - whether splitting is allowed right now
 * @returns {{ action: string, label: string, description: string }}
 */
export function getBasicStrategy(playerCards, dealerUpcard, canDouble = false, canSplit = false) {
  if (!playerCards?.length || !dealerUpcard?.rank) {
    return null;
  }

  const di = dealerIndex(dealerUpcard.rank);
  const { total, soft, count } = handInfo(playerCards);

  // Blackjack — no decision needed
  if (total === 21 && count === 2) {
    return { action: 'S', label: 'Stand', description: 'Blackjack! No action needed.' };
  }

  // Check for pair first (only with exactly 2 cards of same rank)
  if (count === 2 && playerCards[0].rank === playerCards[1].rank) {
    const pairVal = cardValue(playerCards[0].rank);
    const pairRow = PAIR[pairVal];
    if (pairRow) {
      const rec = pairRow[di];
      if (rec === 'P' && canSplit) {
        return { action: 'P', label: 'Split', description: `Split ${playerCards[0].rank}s vs dealer ${dealerUpcard.rank}` };
      }
      // If split recommended but can't split, fall through to hard/soft table
    }
  }

  // Soft hand
  if (soft && SOFT[total]) {
    const rec = SOFT[total][di];
    if (rec === 'D' && canDouble) {
      return { action: 'D', label: 'Double', description: `Soft ${total} — double vs dealer ${dealerUpcard.rank}` };
    }
    if (rec === 'D' || rec === 'H') {
      return { action: 'H', label: 'Hit', description: `Soft ${total} — hit vs dealer ${dealerUpcard.rank}` };
    }
    return { action: 'S', label: 'Stand', description: `Soft ${total} — stand vs dealer ${dealerUpcard.rank}` };
  }

  // Hard hand
  const clampedTotal = Math.max(5, Math.min(20, total));
  const hardRow = HARD[clampedTotal];
  if (hardRow) {
    const rec = hardRow[di];
    if (rec === 'D' && canDouble) {
      return { action: 'D', label: 'Double', description: `Hard ${total} — double vs dealer ${dealerUpcard.rank}` };
    }
    if (rec === 'D' || rec === 'H') {
      return { action: 'H', label: 'Hit', description: `Hard ${total} — hit vs dealer ${dealerUpcard.rank}` };
    }
    return { action: 'S', label: 'Stand', description: `Hard ${total} — stand vs dealer ${dealerUpcard.rank}` };
  }

  // Bust or 21+
  if (total >= 21) {
    return { action: 'S', label: 'Stand', description: 'Stand on 21 or bust.' };
  }

  return { action: 'H', label: 'Hit', description: 'Hit by default.' };
}

export { handInfo, cardValue };
