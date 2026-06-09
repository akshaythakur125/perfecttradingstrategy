import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { signals as signalsApi } from '../services/api';
import { Signal } from '../utils/types';
import { formatPrice, formatDate, getConfidenceColor, getDirectionColor } from '../utils/helpers';

export function TradeSignals() {
  const { data, isLoading } = useQuery({
    queryKey: ['signals'],
    queryFn: () => signalsApi.active(),
  });

  const signals: Signal[] = data?.data || [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Trade Signals</h1>
        <p className="text-gray-400 text-sm mt-1">{signals.length} active signals</p>
      </div>

      {isLoading ? (
        <div className="text-center py-20 text-gray-500">Loading signals...</div>
      ) : signals.length === 0 ? (
        <div className="text-center py-20 text-gray-500">No active signals</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400">
                <th className="text-left py-3 px-4">Symbol</th>
                <th className="text-left py-3 px-4">Direction</th>
                <th className="text-right py-3 px-4">Confidence</th>
                <th className="text-right py-3 px-4">Entry</th>
                <th className="text-right py-3 px-4">SL</th>
                <th className="text-right py-3 px-4">TP1</th>
                <th className="text-right py-3 px-4">R:R</th>
                <th className="text-right py-3 px-4">Generated</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((s) => (
                <tr key={s.id} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                  <td className="py-3 px-4 font-bold">{s.symbol}</td>
                  <td className="py-3 px-4">
                    <span className={`font-semibold ${getDirectionColor(s.direction)}`}>{s.direction}</span>
                  </td>
                  <td className={`py-3 px-4 text-right font-bold ${getConfidenceColor(s.confidence_score)}`}>
                    {s.confidence_score}
                  </td>
                  <td className="py-3 px-4 text-right font-mono">${formatPrice(s.entry_price)}</td>
                  <td className="py-3 px-4 text-right font-mono text-red-400">${formatPrice(s.stop_loss)}</td>
                  <td className="py-3 px-4 text-right font-mono text-green-400">${formatPrice(s.take_profit_1)}</td>
                  <td className="py-3 px-4 text-right">1:{s.risk_reward?.toFixed(1)}</td>
                  <td className="py-3 px-4 text-right text-gray-500">{formatDate(s.generated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
