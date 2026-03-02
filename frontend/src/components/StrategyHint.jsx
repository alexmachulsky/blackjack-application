/**
 * StrategyHint — displays the basic strategy recommendation as a floating badge.
 * Shows the optimal play (Hit/Stand/Double/Split) with a brief explanation.
 */
import { getBasicStrategy } from '../services/basicStrategy';

const ACTION_ICON = {
  H: '👆',
  S: '✋',
  D: '✌️',
  P: '✂️',
};

const ACTION_CLASS = {
  H: 'hint-hit',
  S: 'hint-stand',
  D: 'hint-double',
  P: 'hint-split',
};

export default function StrategyHint({ playerCards, dealerUpcard, canDouble, canSplit }) {
  const hint = getBasicStrategy(playerCards, dealerUpcard, canDouble, canSplit);
  if (!hint) return null;

  return (
    <div className={`strategy-hint ${ACTION_CLASS[hint.action] ?? ''}`}>
      <span className="hint-icon">{ACTION_ICON[hint.action] ?? '?'}</span>
      <div className="hint-text">
        <span className="hint-label">{hint.label}</span>
        <span className="hint-desc">{hint.description}</span>
      </div>
    </div>
  );
}
