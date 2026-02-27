import axios from 'axios';

// Empty base URL — all requests go to the same origin (localhost:3000).
// Vite dev server proxies /auth, /game, /stats, /health to the backend container.
// In production, Nginx handles the same proxying via nginx.conf.
const api = axios.create({
  baseURL: '',
});

export const setAuthToken = (token) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

// ── 401 Interceptor — auto-logout on expired/invalid tokens ─────────────────
let _onUnauthorized = null;

/**
 * Register a callback to be called when any API response returns 401.
 * AuthContext sets this to its logout() function on mount.
 */
export const onUnauthorized = (callback) => {
  _onUnauthorized = callback;
};

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 401 &&
      !error.config?.url?.includes('/auth/login') &&
      !error.config?.url?.includes('/auth/register')
    ) {
      // Token expired or revoked mid-session — trigger logout
      if (_onUnauthorized) _onUnauthorized();
    }
    return Promise.reject(error);
  },
);

// Auth endpoints
export const register = (email, password) => {
  return api.post('/auth/register', { email, password });
};

export const login = (email, password) => {
  return api.post('/auth/login', { email, password });
};

export const getCurrentUser = () => {
  return api.get('/auth/me');
};

// Game endpoints
export const startGame = (betAmount) => {
  return api.post('/game/start', { bet_amount: betAmount });
};

export const hit = (gameId) => {
  return api.post('/game/hit', { game_id: gameId });
};

export const stand = (gameId) => {
  return api.post('/game/stand', { game_id: gameId });
};

/** Phase 1: Double Down — doubles the bet and deals exactly one card. */
export const doubleDown = (gameId) => {
  return api.post('/game/double-down', { game_id: gameId });
};

/** Phase 2: Split — splits a matching-rank pair into two independent hands. */
export const splitHand = (gameId) => {
  return api.post('/game/split', { game_id: gameId });
};

export const getGame = (gameId) => {
  return api.get(`/game/${gameId}`);
};

// Stats endpoints
export const getStats = () => {
  return api.get('/stats');
};

/* ── Namespace exports for components ────────────────────────────────────── */
export const gameApi = {
  startGame,
  hit,
  stand,
  doubleDown,
  split: splitHand,
};

export const statsApi = {
  getStats,
};

export default api;
