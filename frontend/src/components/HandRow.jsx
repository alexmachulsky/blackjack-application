/**
 * HandRow — renders a row of PlayingCards with staggered deal animations.
 * Tracks which cards are newly added to animate only fresh arrivals.
 * Optionally hides the last card face-down (dealer hole card).
 * When `revealAll` is true, previously hidden cards get a 3D flip.
 */
import { useRef, useMemo } from 'react';
import PlayingCard from './PlayingCard';

export default function HandRow({
  cards = [],
  faceDownLast = false,
  revealAll = false,
}) {
  const prevCountRef = useRef(0);

  // Determine which card indices are "new" this render
  const prevCount = prevCountRef.current;
  const newStartIdx = prevCount;

  // Update ref after computing
  useMemo(() => {
    prevCountRef.current = cards.length;
  }, [cards.length]);

  return (
    <div className="hand-row">
      {cards.map((c, i) => {
        const isLast = i === cards.length - 1;
        const isFaceDown = faceDownLast && isLast;
        const isNew = i >= newStartIdx;
        // Flip reveal: card was previously face-down but now being shown
        const flipReveal = revealAll && i >= prevCount - 1 && i > 0 && !isFaceDown;

        return (
          <PlayingCard
            key={`${c.rank}-${c.suit}-${i}`}
            card={c}
            faceDown={isFaceDown}
            dealIndex={isNew ? i - newStartIdx : 0}
            isNew={isNew}
            flipReveal={flipReveal}
          />
        );
      })}
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
