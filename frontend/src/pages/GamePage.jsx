import { useState, useEffect, useContext } from 'react';
import AuthContext from '../context/AuthContext';
import { gameApi, statsApi } from '../services/api';

/* ─── Suit map ───────────────────────────────────────────────────────────── */
const SUIT  = { Hearts: '♥', Diamonds: '♦', Clubs: '♣', Spades: '♠' };
const RED   = new Set(['Hearts', 'Diamonds']);
const FACES = new Set(['K', 'Q', 'J']);

function PlayingCard({ card, faceDown = false }) {
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

function HandRow({ cards = [], faceDownLast = false }) {
  return (
    <div className="hand-row">
      {cards.map((c, i) => (
        <PlayingCard
          key={i}
          card={c}
          faceDown={faceDownLast && i === cards.length - 1}
        />
      ))}
    </div>
  );
}

function GhostHand({ count = 2 }) {
  return (
    <div className="hand-row" style={{ opacity: 0.12 }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card-ghost" />
      ))}
    </div>
  );
}

/* ─── Result helpers ─────────────────────────────────────────────────────── */
function resultClass(r) {
  if (!r) return '';
  const s = r.toLowerCase();
  if (s.includes('blackjack')) return 'blackjack';
  if (s.includes('win'))       return 'win';
  if (s.includes('push') || s.includes('tie')) return 'push';
  return 'lose';
}
function resultLabel(r) {
  if (!r) return '';
  const s = r.toLowerCase();
  if (s.includes('blackjack')) return 'Blackjack! 🎉';
  if (s.includes('win'))       return 'You Win!';
  if (s.includes('push') || s.includes('tie')) return 'Push';
  return 'Dealer Wins';
}

/* ─── Chips ──────────────────────────────────────────────────────────────── */
const CHIPS = [
  { val: 0.5, label: '.50',  cls: 'chip-0-5'  },
  { val: 1,   label: '$1',   cls: 'chip-1'    },
  { val: 5,   label: '$5',   cls: 'chip-5'    },
  { val: 25,  label: '$25',  cls: 'chip-25'   },
  { val: 100, label: '$100', cls: 'chip-100'  },
  { val: 500, label: '$500', cls: 'chip-500'  },
];

/* ══════════════════════════════════════════════════════════════════════════ */
export default function GamePage() {
  const { logout }            = useContext(AuthContext);
  const [balance, setBalance] = useState(1000);
  const [betAmount, setBet]   = useState(0);
  const [game, setGame]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');
  const [stats, setStats]     = useState(null);

  useEffect(() => { fetchStats(); }, []);

  async function fetchStats() {
    try {
      const r = await statsApi.getStats();
      const s = r.data ?? r;
      setStats(s);
      if (s.current_balance != null) setBalance(s.current_balance);
    } catch {}
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

  /* ── Bet helpers ──────────────────────────────────────────────────────── */
  const addChip = (v) => { if (canBet) setBet(b => b + v); };
  const clearBet = () => setBet(0);

  /* ── Deal ─────────────────────────────────────────────────────────────── */
  async function handleDeal() {
    if (betAmount <= 0) { setError('Place a bet first'); return; }
    setError(''); setLoading(true);
    try {
      const r = await gameApi.startGame(betAmount);
      const g = r.data ?? r;
      setGame(g);
      setBalance(b => b - betAmount);
      await fetchStats();
    } catch (e) {
      setError(e.response?.data?.detail ?? 'Failed to start game');
    } finally { setLoading(false); }
  }

  /* ── In-game actions ──────────────────────────────────────────────────── */
  async function handleAction(action) {
    setError(''); setLoading(true);
    const gid = game.game_id;
    try {
      let r;
      if      (action === 'hit')    r = await gameApi.hit(gid);
      else if (action === 'stand')  r = await gameApi.stand(gid);
      else if (action === 'double') r = await gameApi.doubleDown(gid);
      else if (action === 'split')  r = await gameApi.split(gid);
      const g = r.data ?? r;
      setGame(g);
      if (g.status === 'finished') {
        if (g.new_balance != null) setBalance(g.new_balance);
        await fetchStats();
      }
    } catch (e) {
      setError(e.response?.data?.detail ?? 'Action failed');
    } finally { setLoading(false); }
  }

  function handleNewGame() { setGame(null); setBet(0); setError(''); }

  /* ── Render ───────────────────────────────────────────────────────────── */
  return (
    <div className="game-wrapper">

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
                  {stats.win_rate != null ? `${Math.round(stats.win_rate * 100)}%` : '0%'}
                </span>
              </div>
            </>}
          </div>
          <button className="btn-logout" onClick={logout}>Logout</button>
        </header>

        {/* Props */}
        <div className="deck-prop" />
        <div className="table-limits">
          <span>MIN: $5</span>
          <span>MAX: $2000</span>
        </div>

        {/* Table markings */}
        <div className="table-markings">
          <div className="marking-main">BlackJack Pays 3 to 1</div>
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
            ? <HandRow cards={dealerCards} faceDownLast={isPlaying} />
            : <GhostHand />
          }
          {isFinished && dealerValue > 0 && (
            <span className="zone-score">{dealerValue}</span>
          )}
        </div>

        {/* ── Result overlay ───────────────────────────────────────────── */}
        {isFinished && !isSplit && game?.result && (
          <div className="result-overlay" style={{ marginTop: 8 }}>
            <div className={`result-badge ${resultClass(game.result)}`}>
              {resultLabel(game.result)}
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
            {betAmount > 0 && (
              <button className="btn-clear" onClick={clearBet} disabled={loading}>
                Clear
              </button>
            )}
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
                  title="Double Down"
                >
                  <span className="btn-x2">X2</span>
                  <span>DOUBLE</span>
                </button>
              )}

              <button
                className="btn-hit"
                onClick={() => handleAction('hit')}
                disabled={loading}
              >
                HIT
              </button>

              <button
                className="btn-stand"
                onClick={() => handleAction('stand')}
                disabled={loading}
              >
                STAND
              </button>
            </>
          )}
        </div>

        {/* Balance */}
        <div className="balance-box">
          <span className="balance-label">Balance</span>
          <span className="balance-value">${balance.toFixed(2)}</span>
        </div>

      </div>{/* /bottom-strip */}

    </div>
  );
}
