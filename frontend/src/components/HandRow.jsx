/**
 * HandRow — renders a row of PlayingCards.
 * Optionally hides the last card face-down (dealer hole card).
 */
import PlayingCard from './PlayingCard';

export default function HandRow({ cards = [], faceDownLast = false }) {
  return (
    <div className="hand-row">
      {cards.map((c, i) => (
        <PlayingCard
          key={`${c.rank}-${c.suit}-${i}`}
          card={c}
          faceDown={faceDownLast && i === cards.length - 1}
        />
      ))}
    </div>
  );
}

export function GhostHand({ count = 2 }) {
  return (
    <div className="hand-row" style={{ opacity: 0.12 }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card-ghost" />
      ))}
    </div>
  );
}
