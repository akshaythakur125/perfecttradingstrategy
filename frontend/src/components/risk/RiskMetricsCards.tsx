import React from 'react';
import { Shield, TrendingDown, TrendingUp, AlertTriangle } from 'lucide-react';
import { RiskMetrics } from '../../utils/types';
import { Card } from '../common/Card';

interface RiskMetricsCardsProps {
  metrics: RiskMetrics;
}

export function RiskMetricsCards({ metrics }: RiskMetricsCardsProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <Card>
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
      </Card>

      <Card>
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
      </Card>

      <Card>
        <div className="flex items-center gap-3 mb-2">
          <Shield size={20} className="text-blue-400" />
          <span className="text-sm text-gray-500">Open Positions</span>
        </div>
        <div className="text-2xl font-bold">
          {metrics.open_positions} / {metrics.max_open_positions}
        </div>
      </Card>

      <Card>
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
      </Card>
    </div>
  );
}
