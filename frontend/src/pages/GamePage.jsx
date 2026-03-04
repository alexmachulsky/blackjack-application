import { useState, useEffect, useCallback, useContext, useRef } from 'react';
import AuthContext from '../context/AuthContext';
import { gameApi, statsApi } from '../services/api';
import { soundFX } from '../services/soundEffects';
import HandRow, { GhostHand } from '../components/HandRow';
import TableChipStack, { CHIPS } from '../components/TableChipStack';
import Confetti from '../components/Confetti';
import StrategyHint from '../components/StrategyHint';
import { resultClass, resultLabel } from '../utils/resultHelpers';

/* ─── Chips ──────────────────────────────────────────────────────────────── */
// CHIPS and TableChipStack are imported from components/TableChipStack

const getVisiblePlayerCardCount = (state) => {
  if (!state) return 0;
  if (state.is_split && Array.isArray(state.player_hands)) {
    return state.player_hands.reduce(
      (total, hand) => total + (hand?.cards?.length ?? 0),
      0,
    );
  }
  return state.player_hand?.length ?? 0;
};

const getVisibleDealerCardCount = (state) => state?.dealer_hand?.length ?? 0;

function playOutcomeSound(state) {
  const combinedResults = Array.isArray(state?.results)
    ? state.results.join(',')
    : (state?.result ?? '');
  const result = combinedResults.toLowerCase();

  if (result.includes('blackjack')) {
    soundFX.playBlackjack();
  } else if (result.includes('win')) {
    soundFX.playWin();
  } else if (result.includes('push') || result.includes('tie')) {
    soundFX.playPush();
  } else {
    soundFX.playLose();
  }
}

/* ══════════════════════════════════════════════════════════════════════════ */
export default function GamePage({ onShowHistory }) {
  const { logout }            = useContext(AuthContext);
  const initialSound = soundFX.getSettings();
  const [balance, setBalance] = useState(null);
  const [betAmount, setBet]   = useState(0);
  const [game, setGame]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');
  const [stats, setStats]     = useState(null);
  const [soundMuted, setSoundMuted] = useState(initialSound.muted);
  const [soundVolume, setSoundVolume] = useState(initialSound.volume);
  const [showConfetti, setShowConfetti] = useState(false);
  const [hintsOn, setHintsOn] = useState(() => {
    try { return localStorage.getItem('bj_hints') === '1'; } catch { return false; }
  });

  // Ref-based guard against rapid double-clicks (state is async)
  const actionLock = useRef(false);
  // Track timeouts so we can clean up on unmount
  const timeoutsRef = useRef([]);

  const toggleHints = () => {
    const next = !hintsOn;
    setHintsOn(next);
    try { localStorage.setItem('bj_hints', next ? '1' : '0'); } catch { /* noop */ }
  };

  useEffect(() => { fetchStats(); 
    // Cleanup pending timeouts on unmount
    return () => { timeoutsRef.current.forEach(clearTimeout); };
  }, []);

  const armSound = () => {
    soundFX.unlock().catch(() => {});
  };

  async function fetchStats() {
    try {
      const r = await statsApi.getStats();
      const s = r.data ?? r;
      setStats(s);
      if (s.current_balance != null) setBalance(s.current_balance);
    } catch (e) {
      console.error('Failed to fetch stats:', e);
    }
  }

  /* ── API field extraction ─────────────────────────────────────────────── */
  const isPlaying  = game?.status === 'active';
  const isFinished = game?.status === 'finished';
  const canBet     = !game || isFinished;

  const isSplit      = game?.is_split ?? false;
  const splitHands   = game?.player_hands ?? [];
  const splitResults = game?.results ?? [];
  const activeIdx    = game?.current_hand_index ?? 0;

  const playerCards = game?.player_hand  ?? [];
  const playerValue = game?.player_value ?? 0;
  const dealerCards = game?.dealer_hand  ?? [];
  const dealerValue = game?.dealer_value ?? 0;

  const canDouble   = isPlaying && !isSplit && !!game?.can_double_down;
  const canSplit    = isPlaying && !isSplit && !!game?.can_split;
  const tableBetAmount = Number(game?.bet_amount ?? betAmount ?? 0);
  const dealerCardsForDisplay = isPlaying && dealerCards.length === 1
    ? [...dealerCards, { rank: '', suit: '' }]
    : dealerCards;
  const hideDealerLastCard = isPlaying && dealerCardsForDisplay.length > 1;

  /* ── Bet helpers ──────────────────────────────────────────────────────── */
  const MIN_BET = 5;
  const MAX_BET = 2000;

  const addChip = (v) => {
    if (canBet) {
      armSound();
      const next = betAmount + v;
      if (balance != null && next > balance) {
        setError('Bet exceeds your balance');
        soundFX.playError();
        return;
      }
      if (next > MAX_BET) {
        setError(`Maximum bet is $${MAX_BET}`);
        soundFX.playError();
        return;
      }
      soundFX.playChip();
      setBet(next);
    }
  };
  const clearBet = () => {
    armSound();
    soundFX.playButton();
    setBet(0);
  };

  const toggleSound = () => {
    armSound();
    const next = !soundMuted;
    setSoundMuted(next);
    soundFX.setMuted(next);
    if (!next) {
      soundFX.playButton();
    }
  };

  const handleSoundVolume = (e) => {
    const next = Number(e.target.value);
    setSoundVolume(next);
    soundFX.setVolume(next);
  };

  const previewSoundVolume = () => {
    if (!soundMuted) {
      soundFX.playChip();
    }
  };

  const handleLogout = () => {
    armSound();
    soundFX.playButton();
    logout();
  };

  /* ── Deal ─────────────────────────────────────────────────────────────── */
  async function handleDeal() {
    if (actionLock.current) return;
    actionLock.current = true;
    armSound();
    if (betAmount <= 0 || betAmount < MIN_BET) {
      setError(`Minimum bet is $${MIN_BET}`);
      soundFX.playError();
      actionLock.current = false;
      return;
    }
    const savedBalance = balance;
    setError(''); setLoading(true);
    try {
      const r = await gameApi.startGame(betAmount);
      const g = r.data ?? r;
      soundFX.playDealSequence(4, 0.082);
      if (g.status === 'finished') {
        const tid = window.setTimeout(() => playOutcomeSound(g), 420);
        timeoutsRef.current.push(tid);
        if ((g.result ?? '').toLowerCase().includes('blackjack')) {
          setShowConfetti(true);
        }
      }
      setGame(g);
      setBalance(b => b - betAmount);
      await fetchStats();
    } catch (e) {
      soundFX.playError();
      setError(e.response?.data?.detail ?? 'Failed to start game');
      // Rollback optimistic balance on failure
      if (savedBalance != null) setBalance(savedBalance);
    } finally { setLoading(false); actionLock.current = false; }
  }

  /* ── In-game actions ──────────────────────────────────────────────────── */
  async function handleAction(action) {
    if (actionLock.current) return;
    actionLock.current = true;
    armSound();
    setError(''); setLoading(true);
    const previousGame = game;
    const gid = game.game_id;
    try {
      let r;
      if      (action === 'hit')    r = await gameApi.hit(gid);
      else if (action === 'stand')  r = await gameApi.stand(gid);
      else if (action === 'double') r = await gameApi.doubleDown(gid);
      else if (action === 'split')  r = await gameApi.split(gid);
      const g = r.data ?? r;

      if (action === 'hit') soundFX.playHit();
      if (action === 'stand') soundFX.playStand();
      if (action === 'double') soundFX.playDouble();
      if (action === 'split') soundFX.playSplit();

      const dealerDelta = Math.max(
        0,
        getVisibleDealerCardCount(g) - getVisibleDealerCardCount(previousGame),
      );
      const playerDelta = Math.max(
        0,
        getVisiblePlayerCardCount(g) - getVisiblePlayerCardCount(previousGame),
      );

      if (dealerDelta > 0) {
        soundFX.playDealSequence(dealerDelta, 0.09, 0.08);
      } else if (action === 'hit' && playerDelta > 1) {
        soundFX.playDealSequence(playerDelta - 1, 0.08, 0.06);
      }

      if (g.status === 'finished') {
        const resultDelay = dealerDelta > 0 ? 150 + dealerDelta * 90 : 140;
        const tid = window.setTimeout(() => playOutcomeSound(g), resultDelay);
        timeoutsRef.current.push(tid);
        const combined = Array.isArray(g.results) ? g.results.join(',') : (g.result ?? '');
        if (combined.toLowerCase().includes('blackjack')) {
          setShowConfetti(true);
        }
      }

      setGame(g);
      if (g.status === 'finished') {
        if (g.new_balance != null) setBalance(g.new_balance);
        await fetchStats();
      }
    } catch (e) {
      soundFX.playError();
      setError(e.response?.data?.detail ?? 'Action failed');
    } finally { setLoading(false); actionLock.current = false; }
  }

  function handleNewGame() {
    armSound();
    soundFX.playShuffle();
    setGame(null);
    setBet(0);
    setError('');
    setShowConfetti(false);
  }

  /* ── Keyboard shortcuts ───────────────────────────────────────────────── */
  // Use refs to avoid stale closures in the keyboard handler
  const gameRef = useRef(game);
  const loadingRef = useRef(loading);
  useEffect(() => { gameRef.current = game; }, [game]);
  useEffect(() => { loadingRef.current = loading; }, [loading]);

  const handleKeyboard = useCallback((e) => {
    // Ignore if user is typing in an input
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (loadingRef.current || actionLock.current) return;
    const key = e.key.toLowerCase();
    const g = gameRef.current;
    const playing = g?.status === 'active';
    const finished = g?.status === 'finished';
    const dbl = playing && !g?.is_split && !!g?.can_double_down;
    const spl = playing && !g?.is_split && !!g?.can_split;
    if (key === 'h' && playing) handleAction('hit');
    else if (key === 's' && playing) handleAction('stand');
    else if (key === 'd' && dbl) handleAction('double');
    else if (key === 'p' && spl) handleAction('split');
    else if (key === ' ' || key === 'enter') {
      e.preventDefault();
      if (!g && betAmount > 0) handleDeal();
      else if (finished) handleNewGame();
    }
  }, [betAmount]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyboard);
    return () => window.removeEventListener('keydown', handleKeyboard);
  }, [handleKeyboard]);

  /* ── Render ───────────────────────────────────────────────────────────── */
  return (
    <div className="game-wrapper">

      {/* Confetti celebration */}
      {showConfetti && <Confetti onDone={() => setShowConfetti(false)} />}

      {/* ══ TABLE SCENE ═════════════════════════════════════════════════ */}
      <div className="table-scene">

        {/* Felt background */}
        <div className="table-felt" />

        {/* Top bar (brand + stats + logout) */}
        <header className="top-bar">
          <span className="top-bar-brand">♠ BlackJack ♥</span>
          <div className="top-bar-stats">
            {stats && <>
              <div className="stat-pill">
                <span className="stat-label">Games</span>
                <span className="stat-value">{stats.total_games ?? 0}</span>
              </div>
              <div className="stat-pill">
                <span className="stat-label">Wins</span>
                <span className="stat-value">{stats.wins ?? 0}</span>
              </div>
              <div className="stat-pill">
                <span className="stat-label">Win %</span>
                <span className="stat-value">
                  {stats.win_rate != null ? `${Math.round(stats.win_rate)}%` : '0%'}
                </span>
              </div>
              {(stats.current_streak ?? 0) !== 0 && (
                <div className={`stat-pill streak ${stats.current_streak > 0 ? 'streak-win' : 'streak-loss'}`}>
                  <span className="stat-label">Streak</span>
                  <span className="stat-value">
                    {stats.current_streak > 0 ? `${stats.current_streak}W` : `${Math.abs(stats.current_streak)}L`}
                  </span>
                </div>
              )}
            </>}
          </div>
          <div className="top-bar-actions">
            <div className="sound-controls">
              <button
                className={`btn-sound${soundMuted ? ' is-muted' : ''}`}
                onClick={toggleSound}
                title={soundMuted ? 'Unmute sound effects' : 'Mute sound effects'}
              >
                {soundMuted ? 'Sound Off' : 'Sound On'}
              </button>
              <input
                className="sound-slider"
                type="range"
                min="0"
                max="100"
                step="1"
                value={soundVolume}
                onChange={handleSoundVolume}
                onMouseUp={previewSoundVolume}
                onTouchEnd={previewSoundVolume}
                aria-label="Sound effect volume"
                disabled={soundMuted}
              />
            </div>
            <button className="btn-history" onClick={onShowHistory}>
              <span className="btn-icon">📜</span> History
            </button>
            <button
              className={`btn-hints${hintsOn ? ' is-active' : ''}`}
              onClick={toggleHints}
              title={hintsOn ? 'Disable strategy hints' : 'Enable strategy hints'}
            >
              <span className="btn-icon">💡</span> {hintsOn ? 'Hints On' : 'Hints'}
            </button>
            <button className="btn-logout" onClick={handleLogout}>
              <span className="btn-icon">🚪</span> Logout
            </button>
          </div>
        </header>

        {/* Props */}
        <div className="deck-prop" />
        <div className="table-limits">
          <span>MIN: $5</span>
          <span>MAX: $2000</span>
        </div>

        {/* Table markings */}
        <div className="table-markings">
          <div className="marking-main">BlackJack Pays 3 to 2</div>
          <div className="marking-sub">Dealer must draw on 16's and stand on all 17's</div>
          <div className="marking-insurance">Insurance pays 2 to 1</div>
        </div>

        {/* Split FAB */}
        {canSplit && (
          <button className="split-fab" onClick={() => handleAction('split')} disabled={loading}>
            <span className="split-icon">⬦⬦</span>
            <span>SPLIT</span>
          </button>
        )}

        {/* ── Dealer zone ─────────────────────────────────────────────── */}
        <div className="dealer-zone">
          <span className="zone-label">Dealer</span>
          {dealerCards.length > 0
            ? <HandRow cards={dealerCardsForDisplay} faceDownLast={hideDealerLastCard} />
            : <GhostHand />
          }
          {isFinished && dealerValue > 0 && (
            <span className="zone-score">{dealerValue}</span>
          )}
        </div>

        {/* ── Strategy hint overlay ────────────────────────────────────── */}
        {hintsOn && isPlaying && !isSplit && playerCards.length >= 2 && dealerCards.length >= 1 && (
          <StrategyHint
            playerCards={playerCards}
            dealerUpcard={dealerCards[0]}
            canDouble={canDouble}
            canSplit={canSplit}
          />
        )}
        {hintsOn && isPlaying && isSplit && splitHands[activeIdx]?.cards?.length >= 2 && dealerCards.length >= 1 && (
          <StrategyHint
            playerCards={splitHands[activeIdx].cards}
            dealerUpcard={dealerCards[0]}
            canDouble={false}
            canSplit={false}
          />
        )}

        {/* ── Result overlay ───────────────────────────────────────────── */}
        {isFinished && !isSplit && game?.result && (
          <div className="result-overlay" style={{ marginTop: 8 }}>
            <div className={`result-badge ${resultClass(game.result)}`}>
              {resultLabel(game.result, { verbose: true })}
            </div>
            {game.payout != null && (
              <span className="result-payout">
                {game.payout >= 0
                  ? `+$${game.payout.toFixed(0)}`
                  : `-$${Math.abs(game.payout).toFixed(0)}`}
              </span>
            )}
          </div>
        )}
        {isFinished && isSplit && splitResults.length > 0 && (
          <div className="result-overlay" style={{ marginTop: 8 }}>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
              {splitResults.map((res, i) => (
                <div key={i} className={`result-badge ${resultClass(res)}`}
                  style={{ fontSize: '1rem', padding: '7px 18px' }}>
                  Hand {i + 1}: {resultLabel(res)}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Betting zones (table spots) ──────────────────────────────── */}
        <div className="betting-zones">
          <div className="betting-box">
            <div className="bet-ring" />
          </div>

          <div className="betting-box is-center">
            <div className="bet-ring" />
            <TableChipStack amount={tableBetAmount} />

            {/* Player hand inside center spot */}
            <div className="player-zone">
              {!isSplit ? (
                <>
                  {playerCards.length > 0
                    ? <HandRow cards={playerCards} />
                    : <GhostHand />
                  }
                  {playerValue > 0 && (
                    <span className="zone-score">{playerValue}</span>
                  )}
                </>
              ) : (
                <div className="split-hands-row">
                  {splitHands.map((h, i) => (
                    <div
                      key={i}
                      className={`split-hand-block${i === activeIdx ? ' is-active' : ''}`}
                    >
                      <span className="split-hand-label">Hand {i + 1}</span>
                      <HandRow cards={h.cards ?? []} />
                      <span className="split-hand-score">{h.value}</span>
                      {isFinished && splitResults[i] && (
                        <span className={`split-hand-result ${resultClass(splitResults[i])}`}>
                          {resultLabel(splitResults[i])}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
              <span className="zone-label" style={{ marginTop: 4 }}>Player</span>
            </div>
          </div>

          <div className="betting-box">
            <div className="bet-ring" />
          </div>
        </div>

      </div>{/* /table-scene */}

      {/* ══ BOTTOM STRIP ════════════════════════════════════════════════ */}
      <div className="bottom-strip">

        {/* Bet display */}
        <div className="bet-display-box">
          <span className="bet-display-label">Total Bet</span>
          <span className="bet-display-value">
            {(game?.bet_amount ?? betAmount).toFixed(2)}
          </span>
        </div>

        {/* Error */}
        {error && <span className="strip-error">{error}</span>}

        {/* Chip buttons — visible when betting */}
        {canBet && (
          <div className="chip-row">
            {CHIPS.map(({ val, label, cls }) => (
              <button
                key={val}
                className={`chip ${cls}`}
                onClick={() => addChip(val)}
                disabled={loading}
                title={`+${label}`}
              >
                {label}
              </button>
            ))}
            <button
              className={`btn-clear${betAmount > 0 ? '' : ' is-hidden'}`}
              onClick={clearBet}
              disabled={loading || betAmount <= 0}
            >
              Clear
            </button>
          </div>
        )}

        {/* Playing phase — action buttons in middle */}
        {isPlaying && (
          <div className="chip-row">
            <span className="active-bet-info">
              Bet: <span>${game.bet_amount?.toFixed(0)}</span>
            </span>
          </div>
        )}

        {/* Action group (right) */}
        <div className="action-group" style={{ marginLeft: 'auto' }}>
          {/* Between games */}
          {canBet && !isFinished && (
            <button
              className="btn-deal"
              onClick={handleDeal}
              disabled={loading || betAmount <= 0}
            >
              {loading ? 'Dealing…' : 'Deal'}
            </button>
          )}

          {/* Finished */}
          {isFinished && (
            <button className="btn-new-game" onClick={handleNewGame} disabled={loading}>
              New Game
            </button>
          )}

          {/* Playing */}
          {isPlaying && (
            <>
              {canDouble && (
                <button
                  className="btn-double"
                  onClick={() => handleAction('double')}
                  disabled={loading}
                  title="Double Down (D)"
                >
                  <span className="btn-x2">X2</span>
                  <span>DOUBLE</span>
                </button>
              )}

              <button
                className="btn-hit"
                onClick={() => handleAction('hit')}
                disabled={loading}
                title="Hit (H)"
              >
                HIT
              </button>

              <button
                className="btn-stand"
                onClick={() => handleAction('stand')}
                disabled={loading}
                title="Stand (S)"
              >
                STAND
              </button>
            </>
          )}
        </div>

        {/* Balance */}
        <div className="balance-box">
          <span className="balance-label">Balance</span>
          <span className="balance-value">${balance != null ? balance.toFixed(2) : '—'}</span>
        </div>

      </div>{/* /bottom-strip */}

    </div>
  );
}
