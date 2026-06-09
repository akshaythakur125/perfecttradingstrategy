import React from 'react';
import { Signal } from '../../utils/types';
import { formatPrice, getConfidenceBg, getConfidenceColor, getDirectionColor } from '../../utils/helpers';
import { Badge } from '../common/Badge';
import { Card, CardHeader, CardTitle } from '../common/Card';

interface ScannerCardProps {
  signal: Signal;
}

export function ScannerCard({ signal }: ScannerCardProps) {
  return (
    <Card className={getConfidenceBg(signal.confidence_score)}>
      <CardHeader>
        <div className="flex items-center gap-3">
          <CardTitle>{signal.symbol}</CardTitle>
          <Badge variant={signal.direction === 'LONG' ? 'success' : 'danger'}>{signal.direction}</Badge>
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
      </CardHeader>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
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
    </Card>
  );
}
