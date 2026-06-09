import React from 'react';
import { StatCard } from '../common/StatCard';
import { BacktestResult } from '../../utils/types';

interface BacktestMetricsProps {
  result: BacktestResult;
}

export function BacktestMetrics({ result }: BacktestMetricsProps) {
  const metrics = [
    { label: 'Total Trades', value: result.total_trades ?? '-' },
    { label: 'Win Rate', value: `${result.win_rate ?? 0}%`, trend: (result.win_rate ?? 0) >= 50 ? 'up' as const : 'down' as const },
    { label: 'Profit Factor', value: (result.profit_factor ?? 0).toFixed(2), trend: (result.profit_factor ?? 0) >= 1 ? 'up' as const : 'down' as const },
    { label: 'Total PnL', value: `$${(result.total_pnl ?? 0).toFixed(0)}`, color: (result.total_pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400' },
    { label: 'Sharpe', value: (result.sharpe_ratio ?? 0).toFixed(2), trend: (result.sharpe_ratio ?? 0) >= 1 ? 'up' as const : 'down' as const },
    { label: 'Max DD', value: `${result.max_drawdown ?? 0}%`, color: 'text-red-400' },
    { label: 'CAGR', value: `${result.cagr ?? 0}%`, color: (result.cagr ?? 0) >= 0 ? 'text-green-400' : 'text-red-400' },
    { label: 'Avg R:R', value: `1:${(result.average_rr ?? 0).toFixed(1)}` },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
      {metrics.map((m) => (
        <StatCard key={m.label} {...m} />
      ))}
    </div>
  );
}
