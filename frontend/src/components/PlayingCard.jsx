/**
 * PlayingCard — renders a single card face-up or face-down.
 * Supports staggered deal animation via `dealIndex` prop.
 */

const SUIT  = { Hearts: '♥', Diamonds: '♦', Clubs: '♣', Spades: '♠' };
const RED   = new Set(['Hearts', 'Diamonds']);
const FACES = new Set(['K', 'Q', 'J']);

export default function PlayingCard({ card, faceDown = false, dealIndex = 0 }) {
  const animStyle = dealIndex > 0
    ? { animationDelay: `${dealIndex * 0.12}s` }
    : undefined;

  if (faceDown) {
    return <div className="playing-card face-down" style={animStyle} />;
  }

  const color    = RED.has(card.suit) ? 'red' : 'black';
  const isFace   = FACES.has(card.rank);
  const s        = SUIT[card.suit] ?? card.suit;

  return (
    <div
      className={`playing-card ${color}${isFace ? ' face-card' : ''}`}
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
