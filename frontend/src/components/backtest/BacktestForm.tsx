import React from 'react';
import { Play } from 'lucide-react';

const BACKTEST_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT', 'XRPUSDT', 'ADAUSDT'];

interface BacktestFormProps {
  symbol: string;
  capital: number;
  isRunning: boolean;
  onSymbolChange: (symbol: string) => void;
  onCapitalChange: (capital: number) => void;
  onRun: () => void;
}

export function BacktestForm({ symbol, capital, isRunning, onSymbolChange, onCapitalChange, onRun }: BacktestFormProps) {
  return (
    <div className="flex gap-3 items-center">
      <select
        value={symbol}
        onChange={(e) => onSymbolChange(e.target.value)}
        className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white"
      >
        {BACKTEST_SYMBOLS.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>
      <input
        type="number"
        value={capital}
        onChange={(e) => onCapitalChange(Number(e.target.value))}
        className="w-24 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white"
        placeholder="Capital"
      />
      <button
        onClick={onRun}
        disabled={isRunning}
        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-sm transition-colors"
      >
        <Play size={16} className={isRunning ? 'animate-pulse' : ''} />
        {isRunning ? 'Running...' : 'Run Backtest'}
      </button>
    </div>
  );
}
