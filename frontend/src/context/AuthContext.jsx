import React, { createContext, useContext, useState, useEffect } from 'react';
import * as authApi from '../services/api';
import { setAuthToken } from '../services/api';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [token, setToken]  = useState(() => localStorage.getItem('token'));
  const [user,  setUser]   = useState(null);

  /* Re-hydrate user on mount / token change */
  useEffect(() => {
    if (!token) { setUser(null); return; }
    setAuthToken(token);
    authApi.getCurrentUser()
      .then(r => setUser(r.data))
      .catch(() => {
        // Token expired or invalid — clean up
        localStorage.removeItem('token');
        setToken(null);
        setUser(null);
        setAuthToken(null);
      });
  }, [token]);

  /* login(username, password) → calls API, stores token */
  async function login(username, password) {
    const res = await authApi.login(username, password);
    const tok = res.data?.access_token ?? res.data?.token ?? res.data;
    setAuthToken(tok);
    localStorage.setItem('token', tok);
    setToken(tok);
    // user will be populated by the useEffect above
  }

  /* register(username, password) → calls API register */
  async function register(username, password) {
    await authApi.register(username, password);
  }

  function logout() {
    setAuthToken(null);
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, setUser, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export default AuthContext;
