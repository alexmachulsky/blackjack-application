import { AuthProvider, useAuth } from './context/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';
import LoginPage from './pages/LoginPage';
import GamePage from './pages/GamePage';
import './App.css';

function AppContent() {
  const { token } = useAuth();
  return token ? <GamePage /> : <LoginPage />;
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
