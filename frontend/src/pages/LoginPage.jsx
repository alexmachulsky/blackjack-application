import { useState, useContext } from 'react';
import AuthContext from '../context/AuthContext';

export default function LoginPage() {
  const { login, register } = useContext(AuthContext);
  const [mode, setMode]       = useState('login'); // 'login' | 'register'
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register(email, password);
        await login(email, password);
      }
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-bg">
      <div className="login-card">

        <div className="login-logo">
          <div className="suit-row">♠ ♥ ♦ ♣</div>
          <h1>Blackjack</h1>
          <p>Casino Royal</p>
        </div>

        <h2>{mode === 'login' ? 'Sign In' : 'Create Account'}</h2>

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className="input-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              placeholder="Enter password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              required
            />
          </div>

          {error && <div className="login-error">{error}</div>}

          <button
            type="submit"
            className="login-submit"
            disabled={loading || !email || !password}
          >
            {loading
              ? (mode === 'login' ? 'Signing in…' : 'Creating…')
              : (mode === 'login' ? 'Sign In' : 'Create Account')}
          </button>
        </form>

        <hr className="login-divider" />

        <div className="login-toggle">
          {mode === 'login'
            ? <>No account?<button onClick={() => { setMode('register'); setError(''); }}>Register</button></>
            : <>Have an account?<button onClick={() => { setMode('login'); setError(''); }}>Sign In</button></>
          }
        </div>

      </div>
    </div>
  );
}
