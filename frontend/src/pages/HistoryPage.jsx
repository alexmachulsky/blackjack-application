import { useState, useEffect, useCallback } from 'react';
import { statsApi } from '../services/api';
import MiniCard from '../components/MiniCard';

/* ── Result helpers (shared with GamePage — could be extracted later) ──── */
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
  if (s.includes('blackjack')) return 'Blackjack!';
  if (s.includes('win'))       return 'Win';
  if (s.includes('push') || s.includes('tie')) return 'Push';
  return 'Loss';
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const PAGE_SIZE = 15;

export default function HistoryPage({ onBack }) {
  const [games, setGames]       = useState([]);
  const [page, setPage]         = useState(1);
  const [total, setTotal]       = useState(0);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const fetchPage = useCallback(async (p) => {
    setLoading(true);
    setError('');
    try {
      const r = await statsApi.getHistory(p, PAGE_SIZE);
      const d = r.data ?? r;
      setGames(d.games);
      setTotal(d.total);
      setPage(d.page);
    } catch {
      setError('Failed to load game history');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPage(1); }, [fetchPage]);

  const goPrev = () => { if (page > 1) fetchPage(page - 1); };
  const goNext = () => { if (page < totalPages) fetchPage(page + 1); };

  return (
    <div className="history-page">
      {/* Top bar */}
      <header className="history-header">
        <button className="btn-back" onClick={onBack}>← Back to Table</button>
        <h1 className="history-title">Game History</h1>
        <span className="history-count">{total} game{total !== 1 ? 's' : ''}</span>
      </header>

      {error && <p className="history-error">{error}</p>}

      {loading ? (
        <div className="history-loading">Loading…</div>
      ) : games.length === 0 ? (
        <div className="history-empty">No games played yet. Hit the tables!</div>
      ) : (
        <>
          <div className="history-list">
            {games.map((g) => (
              <div key={g.game_id} className={`history-card ${resultClass(g.result)}`}>
                {/* Header row */}
                <div className="hc-top">
                  <span className={`hc-result ${resultClass(g.result)}`}>
                    {g.result
                      ? g.result.split(',').map((r, i) => (
                          <span key={i} className={`hc-result-tag ${resultClass(r)}`}>
                            {g.is_split ? `H${i + 1}: ` : ''}{resultLabel(r)}
                          </span>
                        ))
                      : '—'}
                  </span>
                  <span className="hc-bet">${g.bet_amount.toFixed(2)}</span>
                </div>

                {/* Cards row */}
                <div className="hc-hands">
                  <div className="hc-hand">
                    <span className="hc-hand-label">Player</span>
                    <div className="hc-cards">
                      {g.player_cards.map((c, i) => (
                        <MiniCard key={`p-${i}`} rank={c.rank} suit={c.suit} />
                      ))}
                    </div>
                  </div>
                  <span className="hc-vs">vs</span>
                  <div className="hc-hand">
                    <span className="hc-hand-label">Dealer</span>
                    <div className="hc-cards">
                      {g.dealer_cards.map((c, i) => (
                        <MiniCard key={`d-${i}`} rank={c.rank} suit={c.suit} />
                      ))}
                    </div>
                  </div>
                </div>

                {/* Footer */}
                <div className="hc-footer">
                  <span className="hc-date">{formatDate(g.created_at)}</span>
                  {g.is_split && <span className="hc-split-badge">SPLIT</span>}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="history-pagination">
              <button onClick={goPrev} disabled={page <= 1}>‹ Prev</button>
              <span className="history-page-info">
                Page {page} of {totalPages}
              </span>
              <button onClick={goNext} disabled={page >= totalPages}>Next ›</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
