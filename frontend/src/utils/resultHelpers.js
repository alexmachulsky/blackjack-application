/**
 * Shared result helper functions for game outcome display.
 * Used by both GamePage and HistoryPage.
 */

export function resultClass(r) {
  if (!r) return '';
  const s = r.toLowerCase();
  if (s.includes('blackjack')) return 'blackjack';
  if (s.includes('win'))       return 'win';
  if (s.includes('push') || s.includes('tie')) return 'push';
  return 'lose';
}

export function resultLabel(r, { verbose = false } = {}) {
  if (!r) return '';
  const s = r.toLowerCase();
  if (s.includes('blackjack')) return verbose ? 'Blackjack! 🎉' : 'Blackjack!';
  if (s.includes('win'))       return verbose ? 'You Win!' : 'Win';
  if (s.includes('push') || s.includes('tie')) return 'Push';
  return verbose ? 'Dealer Wins' : 'Loss';
}
