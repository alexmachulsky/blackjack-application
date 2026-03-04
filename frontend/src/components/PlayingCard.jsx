/**
 * PlayingCard — renders a single card face-up or face-down.
 * Supports staggered deal animation via `dealIndex` prop.
 * Supports 3D flip reveal via `flipReveal` prop (dealer hole card).
 */
import { useState, useEffect } from 'react';

const SUIT  = { Hearts: '♥', Diamonds: '♦', Clubs: '♣', Spades: '♠' };
const RED   = new Set(['Hearts', 'Diamonds']);
const FACES = new Set(['K', 'Q', 'J']);

export default function PlayingCard({
  card,
  faceDown = false,
  dealIndex = 0,
  isNew = false,
  flipReveal = false,
}) {
  const [flipped, setFlipped] = useState(flipReveal);

  useEffect(() => {
    if (flipReveal) {
      // Short delay so the flip starts after the component mounts
      const t = setTimeout(() => setFlipped(false), 60);
      return () => clearTimeout(t);
    }
  }, [flipReveal]);

  const dealDelay = dealIndex * 0.14;
  const animClass = isNew ? 'card-deal-in' : '';
  const animStyle = {
    animationDelay: `${dealDelay}s`,
    '--deal-delay': `${dealDelay}s`,
  };

  // 3D flip wrapper for the dealer reveal
  if (flipReveal) {
    return (
      <div
        className={`card-flip-container ${animClass} ${flipped ? 'is-flipped' : ''}`}
        style={animStyle}
      >
        <div className="card-flip-inner">
          <div className="card-flip-front">
            <CardFace card={card} />
          </div>
          <div className="card-flip-back">
            <div className="playing-card face-down" />
          </div>
        </div>
      </div>
    );
  }

  if (faceDown) {
    return (
      <div
        className={`playing-card face-down ${animClass}`}
        style={animStyle}
      />
    );
  }

  return <CardFace card={card} animClass={animClass} animStyle={animStyle} />;
}

function CardFace({ card, animClass = '', animStyle = {} }) {
  const color  = RED.has(card.suit) ? 'red' : 'black';
  const isFace = FACES.has(card.rank);
  const s      = SUIT[card.suit] ?? card.suit;

  return (
    <div
      className={`playing-card ${color}${isFace ? ' face-card' : ''} ${animClass}`}
      style={animStyle}
    >
      <div className="card-corner">
        <span className="cr">{card.rank}</span>
        <span className="cs">{s}</span>
      </div>
      <div className="card-center">{s}</div>
      <div className="card-corner bottom">
        <span className="cr">{card.rank}</span>
        <span className="cs">{s}</span>
      </div>
    </div>
  );
}

export { SUIT, RED, FACES };
