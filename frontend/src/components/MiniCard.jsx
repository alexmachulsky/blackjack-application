/**
 * MiniCard — compact card representation for history/summary views.
 * Shows rank + suit symbol at a small size.
 */

const SUIT = { Hearts: '♥', Diamonds: '♦', Clubs: '♣', Spades: '♠' };
const RED  = new Set(['Hearts', 'Diamonds']);

export default function MiniCard({ rank, suit }) {
  const color = RED.has(suit) ? 'red' : 'black';
  const s     = SUIT[suit] ?? suit;
  return (
    <span className={`mini-card ${color}`}>
      {rank}{s}
    </span>
  );
}
