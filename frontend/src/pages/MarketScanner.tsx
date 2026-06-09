import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { scanner } from '../services/api';
import { Signal } from '../utils/types';
import { formatPrice, getDirectionColor, getConfidenceColor, getConfidenceBg } from '../utils/helpers';
import { Scan, Filter, RefreshCw } from 'lucide-react';

export function MarketScanner() {
  const [exchange, setExchange] = useState('BINANCE');
  const [limit, setLimit] = useState(30);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['scanner', exchange, limit],
    queryFn: () => scanner.scan(exchange, limit),
  });

  const signals: Signal[] = data?.data?.signals || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Market Scanner</h1>
          <p className="text-gray-400 text-sm mt-1">
            {data?.data?.scanned_pairs || 0} pairs scanned &middot; {signals.length} signals found
          </p>
        </div>
        <div className="flex gap-3">
          <select
            value={exchange}
            onChange={(e) => setExchange(e.target.value)}
            className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white"
          >
            <option value="BINANCE">Binance</option>
            <option value="OKX">OKX</option>
          </select>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white"
          >
            <option value={10}>Top 10</option>
            <option value={30}>Top 30</option>
            <option value={50}>Top 50</option>
          </select>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm transition-colors"
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            Scan
          </button>
        </div>
      </div>

      {isLoading && signals.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <Scan size={48} className="mx-auto mb-4 opacity-30" />
          <p>Scanning markets...</p>
        </div>
      ) : signals.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <Scan size={48} className="mx-auto mb-4 opacity-30" />
          <p>No signals found. Try scanning more pairs.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {signals.map((signal) => (
            <SignalCard key={signal.id || signal.symbol + signal.direction} signal={signal} />
          ))}
        </div>
      )}
    </div>
  );
}

function SignalCard({ signal }: { signal: Signal }) {
  return (
    <div className={`p-5 rounded-xl border ${getConfidenceBg(signal.confidence_score)}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-bold">{signal.symbol}</h3>
          <span className={`px-2 py-0.5 rounded text-xs font-bold ${
            signal.direction === 'LONG' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          }`}>
            {signal.direction}
          </span>
          <span className={`text-sm font-semibold ${getDirectionColor(signal.direction)}`}>
            {signal.trend_direction}
          </span>
        </div>
        <div className="text-right">
          <div className={`text-2xl font-bold ${getConfidenceColor(signal.confidence_score)}`}>
            {signal.confidence_score}
          </div>
          <div className="text-xs text-gray-500">Confidence</div>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Entry</span>
          <div className="font-mono font-bold">${formatPrice(signal.entry_price)}</div>
        </div>
        <div>
          <span className="text-gray-500">Stop Loss</span>
          <div className="font-mono text-red-400">${formatPrice(signal.stop_loss)}</div>
        </div>
        <div>
          <span className="text-gray-500">TP1</span>
          <div className="font-mono text-green-400">${formatPrice(signal.take_profit_1)}</div>
        </div>
        <div>
          <span className="text-gray-500">R:R</span>
          <div className="font-mono font-bold">1:{signal.risk_reward.toFixed(1)}</div>
        </div>
      </div>
      {signal.reasons && signal.reasons.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-700/50">
          <div className="flex flex-wrap gap-2">
            {signal.reasons.slice(0, 5).map((reason, i) => (
              <span key={i} className="px-2 py-1 bg-gray-800 rounded text-xs text-gray-300">
                {reason}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
