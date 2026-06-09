import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { trades } from '../services/api';
import { BookOpen } from 'lucide-react';

export function TradeJournal() {
  const { data, isLoading } = useQuery({
    queryKey: ['trades-journal'],
    queryFn: () => trades.list({ limit: 50 }),
  });

  const allTrades = data?.data || [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Trade Journal</h1>
        <p className="text-gray-400 text-sm mt-1">{allTrades.length} trades recorded</p>
      </div>

      {isLoading ? (
        <div className="text-center py-20 text-gray-500">Loading...</div>
      ) : allTrades.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <BookOpen size={48} className="mx-auto mb-4 opacity-30" />
          <p>No trades recorded yet</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400">
                <th className="text-left py-3 px-4">Date</th>
                <th className="text-left py-3 px-4">Symbol</th>
                <th className="text-left py-3 px-4">Direction</th>
                <th className="text-right py-3 px-4">Entry</th>
                <th className="text-right py-3 px-4">Exit</th>
                <th className="text-right py-3 px-4">Size</th>
                <th className="text-right py-3 px-4">P&L</th>
                <th className="text-right py-3 px-4">R:R</th>
                <th className="text-left py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {allTrades.map((t: any) => (
                <tr key={t.id} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                  <td className="py-3 px-4 text-gray-500">{new Date(t.created_at).toLocaleDateString()}</td>
                  <td className="py-3 px-4 font-bold">{t.symbol}</td>
                  <td className={`py-3 px-4 font-semibold ${t.direction === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>
                    {t.direction}
                  </td>
                  <td className="py-3 px-4 text-right font-mono">${t.entry_price?.toFixed(2)}</td>
                  <td className="py-3 px-4 text-right font-mono">${t.exit_price?.toFixed(2) || '-'}</td>
                  <td className="py-3 px-4 text-right font-mono">{t.position_size?.toFixed(4) || '-'}</td>
                  <td className={`py-3 px-4 text-right font-bold ${(t.pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {t.pnl ? `$${t.pnl.toFixed(2)}` : '-'}
                  </td>
                  <td className="py-3 px-4 text-right">{t.risk_reward ? `1:${t.risk_reward.toFixed(1)}` : '-'}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      t.status === 'CLOSED' ? 'bg-gray-700 text-gray-300' :
                      t.status === 'ACTIVE' ? 'bg-green-500/20 text-green-400' :
                      'bg-yellow-500/20 text-yellow-400'
                    }`}>
                      {t.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
