/**
 * DailyBonusModal — animated popup for claiming the daily login bonus.
 * Shows streak info, bonus amount, and a claim button.
 */
import { useState } from 'react';

export default function DailyBonusModal({
  streak = 0,
  bonusAmount = 50,
  onClaim,
  onClose,
}) {
  const [claiming, setClaiming] = useState(false);
  const [claimed, setClaimed] = useState(false);
  const [claimResult, setClaimResult] = useState(null);

  const handleClaim = async () => {
    if (claiming || claimed) return;
    setClaiming(true);
    try {
      const result = await onClaim();
      setClaimResult(result);
      setClaimed(true);
    } catch {
      setClaiming(false);
    }
  };

  const streakDots = Array.from({ length: 7 }, (_, i) => (
    <span
      key={i}
      className={`streak-dot ${i < streak ? 'active' : ''} ${i === streak - 1 ? 'current' : ''}`}
    >
      {i < streak ? '★' : '☆'}
    </span>
  ));

  return (
    <div className="bonus-overlay" onClick={claimed ? onClose : undefined}>
      <div className="bonus-modal" onClick={(e) => e.stopPropagation()}>
        {!claimed ? (
          <>
            <div className="bonus-icon">🎁</div>
            <h2 className="bonus-title">Daily Bonus!</h2>
            <p className="bonus-subtitle">Welcome back! Claim your free chips.</p>

            <div className="bonus-streak-track">{streakDots}</div>
            <p className="bonus-streak-label">
              Day {streak} streak
              {streak > 1 && ' 🔥'}
            </p>

            <div className="bonus-amount">
              <span className="bonus-dollar">$</span>
              <span className="bonus-value">{bonusAmount}</span>
            </div>

            <button
              className="bonus-claim-btn"
              onClick={handleClaim}
              disabled={claiming}
            >
              {claiming ? 'Claiming…' : 'CLAIM BONUS'}
            </button>

            <button className="bonus-skip-btn" onClick={onClose}>
              Skip for now
            </button>
          </>
        ) : (
          <>
            <div className="bonus-icon bonus-icon-celebrate">🎉</div>
            <h2 className="bonus-title">Bonus Claimed!</h2>
            <div className="bonus-amount claimed">
              <span className="bonus-dollar">+$</span>
              <span className="bonus-value">
                {claimResult?.bonus_amount ?? bonusAmount}
              </span>
            </div>
            <p className="bonus-balance">
              New balance: ${claimResult?.new_balance?.toLocaleString() ?? '—'}
            </p>
            <p className="bonus-message">{claimResult?.message ?? ''}</p>
            <button className="bonus-claim-btn" onClick={onClose}>
              LET&apos;S PLAY!
            </button>
          </>
        )}
      </div>
    </div>
  );
}
