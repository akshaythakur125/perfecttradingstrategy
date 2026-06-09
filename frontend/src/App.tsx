import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DashboardLayout } from './components/dashboard/DashboardLayout';
import { MarketScanner } from './pages/MarketScanner';
import { TradeSignals } from './pages/TradeSignals';
import { OpenPositions } from './pages/OpenPositions';
import { BacktestResults } from './pages/BacktestResults';
import { TradeJournal } from './pages/TradeJournal';
import { RiskDashboard } from './pages/RiskDashboard';
import { PerformanceAnalytics } from './pages/PerformanceAnalytics';
import { Login } from './pages/Login';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchInterval: 30000,
      staleTime: 10000,
      retry: 2,
    },
  },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/scanner" replace />} />
            <Route path="scanner" element={<MarketScanner />} />
            <Route path="signals" element={<TradeSignals />} />
            <Route path="positions" element={<OpenPositions />} />
            <Route path="backtest" element={<BacktestResults />} />
            <Route path="journal" element={<TradeJournal />} />
            <Route path="risk" element={<RiskDashboard />} />
            <Route path="analytics" element={<PerformanceAnalytics />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
