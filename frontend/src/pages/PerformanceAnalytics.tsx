import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { backtest } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp } from 'lucide-react';

export function PerformanceAnalytics() {
  const { data } = useQuery({
    queryKey: ['backtest-latest'],
    queryFn: () => backtest.history(1),
  });

  const latest = data?.data?.[0];

  if (!latest) {
    return (
      <div>
        <div className="mb-6">
          <h1 className="text-2xl font-bold">Performance Analytics</h1>
          <p className="text-gray-400 text-sm mt-1">Run a backtest to see analytics</p>
        </div>
        <div className="text-center py-20 text-gray-500">
          <TrendingUp size={48} className="mx-auto mb-4 opacity-30" />
          <p>No backtest data available</p>
        </div>
      </div>
    );
  }

  const monthlyData = latest.monthly_performance
    ? Object.entries(latest.monthly_performance).map(([month, pnl]) => ({ month, pnl }))
    : [];

  const winLossData = [
    { name: 'Wins', value: latest.winning_trades || 0 },
    { name: 'Losses', value: latest.losing_trades || 0 },
  ];

  const COLORS = ['#22c55e', '#ef4444'];

  const metrics = [
    { label: 'Win Rate', value: `${latest.win_rate}%` },
    { label: 'Profit Factor', value: latest.profit_factor?.toFixed(2) },
    { label: 'Sharpe Ratio', value: latest.sharpe_ratio?.toFixed(2) },
    { label: 'Sortino Ratio', value: latest.sortino_ratio?.toFixed(2) },
    { label: 'Max Drawdown', value: `${latest.max_drawdown}%` },
    { label: 'CAGR', value: `${latest.cagr}%` },
    { label: 'Avg Holding Time', value: `${latest.average_holding_time?.toFixed(1)}h` },
    { label: 'Avg R:R', value: `1:${latest.average_rr?.toFixed(1)}` },
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Performance Analytics</h1>
        <p className="text-gray-400 text-sm mt-1">{latest.symbol} &middot; {latest.total_trades} trades</p>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        {metrics.map((m) => (
          <div key={m.label} className="p-4 bg-gray-900 rounded-xl border border-gray-800">
            <div className="text-sm text-gray-500">{m.label}</div>
            <div className="text-xl font-bold">{m.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {monthlyData.length > 0 && (
          <div className="p-4 bg-gray-900 rounded-xl border border-gray-800">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Monthly Performance</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={monthlyData}>
                <XAxis dataKey="month" tick={{ fill: '#666', fontSize: 10 }} />
                <YAxis hide />
                <Tooltip
                  contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: '8px' }}
                  labelStyle={{ color: '#999' }}
                />
                <Bar dataKey="pnl" fill="#22c55e" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="p-4 bg-gray-900 rounded-xl border border-gray-800">
          <h3 className="text-sm font-semibold text-gray-400 mb-3">Win / Loss Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={winLossData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {winLossData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: '8px' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
