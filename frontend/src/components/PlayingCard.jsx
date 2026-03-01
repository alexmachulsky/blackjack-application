/**
 * PlayingCard — renders a single card face-up or face-down.
 * Extracted from GamePage for reusability and cleaner architecture.
 */

const SUIT  = { Hearts: '♥', Diamonds: '♦', Clubs: '♣', Spades: '♠' };
const RED   = new Set(['Hearts', 'Diamonds']);
const FACES = new Set(['K', 'Q', 'J']);

export default function PlayingCard({ card, faceDown = false }) {
  if (faceDown) return <div className="playing-card face-down" />;
  const color    = RED.has(card.suit) ? 'red' : 'black';
  const isFace   = FACES.has(card.rank);
  const s        = SUIT[card.suit] ?? card.suit;
  return (
    <div className={`playing-card ${color}${isFace ? ' face-card' : ''}`}>
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
