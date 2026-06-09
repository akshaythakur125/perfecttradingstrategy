import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { trades } from '../services/api';
import { Trade } from '../utils/types';
import { formatPrice, formatDate, formatCurrency, getDirectionColor } from '../utils/helpers';

export function OpenPositions() {
  const { data, isLoading } = useQuery({
    queryKey: ['positions'],
    queryFn: () => trades.open(),
  });

  const positions: Trade[] = data?.data || [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Open Positions</h1>
        <p className="text-gray-400 text-sm mt-1">{positions.length} open positions</p>
      </div>

      {isLoading ? (
        <div className="text-center py-20 text-gray-500">Loading positions...</div>
      ) : positions.length === 0 ? (
        <div className="text-center py-20 text-gray-500">No open positions</div>
      ) : (
        <div className="grid gap-4">
          {positions.map((trade) => (
            <div key={trade.id} className="p-5 bg-gray-900 rounded-xl border border-gray-800">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <h3 className="text-lg font-bold">{trade.symbol}</h3>
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                    trade.direction === 'LONG' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {trade.direction}
                  </span>
                </div>
                {trade.pnl !== undefined && (
                  <div className={`text-lg font-bold ${trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {formatCurrency(trade.pnl)}
                    {trade.pnl_percent !== undefined && (
                      <span className="text-sm ml-1">({trade.pnl_percent >= 0 ? '+' : ''}{trade.pnl_percent?.toFixed(2)}%)</span>
                    )}
                  </div>
                )}
              </div>
              <div className="grid grid-cols-5 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Entry</span>
                  <div className="font-mono">${formatPrice(trade.entry_price)}</div>
                </div>
                <div>
                  <span className="text-gray-500">SL</span>
                  <div className="font-mono text-red-400">${formatPrice(trade.stop_loss)}</div>
                </div>
                <div>
                  <span className="text-gray-500">Size</span>
                  <div className="font-mono">{trade.position_size?.toFixed(4)}</div>
                </div>
                <div>
                  <span className="text-gray-500">Risk</span>
                  <div className="font-mono">{formatCurrency(trade.dollar_risk || 0)}</div>
                </div>
                <div>
                  <span className="text-gray-500">R:R</span>
                  <div className="font-mono">1:{trade.risk_reward?.toFixed(1)}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
