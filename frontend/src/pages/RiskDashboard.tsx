import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { risk } from '../services/api';
import { RiskMetrics as RiskMetricsType } from '../utils/types';
import { Shield, TrendingDown, TrendingUp, AlertTriangle } from 'lucide-react';

export function RiskDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['risk-metrics'],
    queryFn: () => risk.metrics(),
    refetchInterval: 5000,
  });

  const metrics: RiskMetricsType = data?.data || {} as RiskMetricsType;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Risk Dashboard</h1>
        <p className="text-gray-400 text-sm mt-1">Real-time risk monitoring</p>
      </div>

      {isLoading ? (
        <div className="text-center py-20 text-gray-500">Loading...</div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="p-5 bg-gray-900 rounded-xl border border-gray-800">
            <div className="flex items-center gap-3 mb-2">
              <TrendingUp size={20} className={metrics.daily_pnl >= 0 ? 'text-green-400' : 'text-red-400'} />
              <span className="text-sm text-gray-500">Daily P&L</span>
            </div>
            <div className={`text-2xl font-bold ${metrics.daily_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              ${metrics.daily_pnl?.toFixed(2)}
            </div>
            <div className={`text-sm ${metrics.daily_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {metrics.daily_pnl_percent?.toFixed(2)}%
            </div>
          </div>

          <div className="p-5 bg-gray-900 rounded-xl border border-gray-800">
            <div className="flex items-center gap-3 mb-2">
              <TrendingDown size={20} className={metrics.weekly_pnl >= 0 ? 'text-green-400' : 'text-red-400'} />
              <span className="text-sm text-gray-500">Weekly P&L</span>
            </div>
            <div className={`text-2xl font-bold ${metrics.weekly_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              ${metrics.weekly_pnl?.toFixed(2)}
            </div>
            <div className={`text-sm ${metrics.weekly_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {metrics.weekly_pnl_percent?.toFixed(2)}%
            </div>
          </div>

          <div className="p-5 bg-gray-900 rounded-xl border border-gray-800">
            <div className="flex items-center gap-3 mb-2">
              <Shield size={20} className="text-blue-400" />
              <span className="text-sm text-gray-500">Open Positions</span>
            </div>
            <div className="text-2xl font-bold">
              {metrics.open_positions} / {metrics.max_open_positions}
            </div>
          </div>

          <div className="p-5 bg-gray-900 rounded-xl border border-gray-800">
            <div className="flex items-center gap-3 mb-2">
              <AlertTriangle size={20} className={metrics.daily_loss_limit_hit ? 'text-red-400' : 'text-green-400'} />
              <span className="text-sm text-gray-500">Risk Status</span>
            </div>
            <div className="text-2xl font-bold">
              {metrics.daily_loss_limit_hit ? 'BREACH' : metrics.weekly_loss_limit_hit ? 'WEEKLY BREACH' : 'OK'}
            </div>
            <div className="text-sm text-gray-500">
              Risk/Trade: {(metrics.current_risk_per_trade * 100).toFixed(0)}%
            </div>
          </div>
        </div>
      )}

      <div className="p-5 bg-gray-900 rounded-xl border border-gray-800">
        <h2 className="text-lg font-semibold mb-4">Risk Management Rules</h2>
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Risk Per Trade</span>
              <span className="font-mono">1%</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Max Open Positions</span>
              <span className="font-mono">3</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Daily Loss Limit</span>
              <span className="font-mono">3%</span>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Weekly Loss Limit</span>
              <span className="font-mono">8%</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Min Risk/Reward</span>
              <span className="font-mono">1:3</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Position Sizing</span>
              <span className="font-mono">Dynamic (ATR)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
