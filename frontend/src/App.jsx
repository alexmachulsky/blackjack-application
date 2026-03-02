import { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';
import LoginPage from './pages/LoginPage';
import GamePage from './pages/GamePage';
import HistoryPage from './pages/HistoryPage';
import './App.css';

function AppContent() {
  const { token } = useAuth();
  const [view, setView] = useState('game'); // 'game' | 'history'

  if (!token) return <LoginPage />;

  if (view === 'history') {
    return <HistoryPage onBack={() => setView('game')} />;
  }

  return <GamePage onShowHistory={() => setView('history')} />;
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
