import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { backtest } from '../services/api';
import { BacktestResult } from '../utils/types';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { Play } from 'lucide-react';

const BACKTEST_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT', 'XRPUSDT', 'ADAUSDT'];

export function BacktestResults() {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [capital, setCapital] = useState(10000);

  const { data: history, isLoading: histLoading } = useQuery({
    queryKey: ['backtest-history'],
    queryFn: () => backtest.history(10),
  });

  const runMutation = useMutation({
    mutationFn: () => backtest.run({ symbol, initial_capital: capital }),
  });

  const results: BacktestResult[] = history?.data || [];
  const latestRun = runMutation.data?.data;

  const equityData = latestRun?.equity_curve?.map((val: number, i: number) => ({ bar: i, equity: val })) || [];
  const monthlyData = latestRun?.monthly_performance
    ? Object.entries(latestRun.monthly_performance).map(([month, pnl]) => ({ month, pnl }))
    : [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Backtest Engine</h1>
        <div className="flex gap-3 items-center">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white"
          >
            {BACKTEST_SYMBOLS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <input
            type="number"
            value={capital}
            onChange={(e) => setCapital(Number(e.target.value))}
            className="w-24 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white"
            placeholder="Capital"
          />
          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-sm transition-colors"
          >
            <Play size={16} />
            Run Backtest
          </button>
        </div>
      </div>

      {runMutation.isPending && (
        <div className="text-center py-10 text-gray-500">Running backtest...</div>
      )}

      {latestRun && (
        <div className="mb-8">
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[
              { label: 'Total Trades', value: latestRun.total_trades },
              { label: 'Win Rate', value: `${latestRun.win_rate}%` },
              { label: 'Profit Factor', value: latestRun.profit_factor?.toFixed(2) },
              { label: 'Total PnL', value: `$${latestRun.total_pnl?.toFixed(0)}`, color: (latestRun.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400' },
              { label: 'Sharpe', value: latestRun.sharpe_ratio?.toFixed(2) },
              { label: 'Max DD', value: `${latestRun.max_drawdown}%`, color: 'text-red-400' },
              { label: 'CAGR', value: `${latestRun.cagr}%`, color: (latestRun.cagr || 0) >= 0 ? 'text-green-400' : 'text-red-400' },
              { label: 'Avg R:R', value: `1:${latestRun.average_rr?.toFixed(1)}` },
            ].map((m) => (
              <div key={m.label} className="p-4 bg-gray-900 rounded-xl border border-gray-800">
                <div className="text-sm text-gray-500">{m.label}</div>
                <div className={`text-xl font-bold ${m.color || 'text-white'}`}>{m.value}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-6">
            {equityData.length > 0 && (
              <div className="p-4 bg-gray-900 rounded-xl border border-gray-800">
                <h3 className="text-sm font-semibold text-gray-400 mb-3">Equity Curve</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={equityData}>
                    <XAxis dataKey="bar" hide />
                    <YAxis domain={['auto', 'auto']} hide />
                    <Tooltip
                      contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: '8px' }}
                      labelStyle={{ color: '#999' }}
                    />
                    <Line type="monotone" dataKey="equity" stroke="#3b82f6" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
            {monthlyData.length > 0 && (
              <div className="p-4 bg-gray-900 rounded-xl border border-gray-800">
                <h3 className="text-sm font-semibold text-gray-400 mb-3">Monthly Performance</h3>
                <ResponsiveContainer width="100%" height={250}>
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
          </div>
        </div>
      )}

      <div>
        <h2 className="text-lg font-semibold mb-4">Backtest History</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400">
                <th className="text-left py-3 px-4">Symbol</th>
                <th className="text-right py-3 px-4">Trades</th>
                <th className="text-right py-3 px-4">Win Rate</th>
                <th className="text-right py-3 px-4">Profit Factor</th>
                <th className="text-right py-3 px-4">Sharpe</th>
                <th className="text-right py-3 px-4">Max DD</th>
                <th className="text-right py-3 px-4">CAGR</th>
                <th className="text-right py-3 px-4">Created</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.id} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                  <td className="py-3 px-4 font-bold">{r.symbol}</td>
                  <td className="py-3 px-4 text-right">{r.total_trades}</td>
                  <td className="py-3 px-4 text-right text-green-400">{r.win_rate}%</td>
                  <td className="py-3 px-4 text-right">{r.profit_factor?.toFixed(2)}</td>
                  <td className="py-3 px-4 text-right">{r.sharpe_ratio?.toFixed(2)}</td>
                  <td className="py-3 px-4 text-right text-red-400">{r.max_drawdown}%</td>
                  <td className="py-3 px-4 text-right">{r.cagr}%</td>
                  <td className="py-3 px-4 text-right text-gray-500">{new Date(r.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
