import React from 'react';
import { Signal } from '../../utils/types';
import { formatPrice, formatDate, getConfidenceColor, getDirectionColor } from '../../utils/helpers';
import { Badge } from '../common/Badge';
import { DataTable, Column } from '../common/DataTable';

interface SignalsTableProps {
  signals: Signal[];
  isLoading?: boolean;
}

export function SignalsTable({ signals, isLoading }: SignalsTableProps) {
  const columns: Column<Signal>[] = [
    { key: 'symbol', label: 'Symbol', render: (s) => <span className="font-bold">{s.symbol}</span> },
    {
      key: 'direction', label: 'Direction',
      render: (s) => <Badge variant={s.direction === 'LONG' ? 'success' : 'danger'}>{s.direction}</Badge>,
    },
    {
      key: 'confidence', label: 'Confidence', align: 'right',
      render: (s) => <span className={`font-bold ${getConfidenceColor(s.confidence_score)}`}>{s.confidence_score}</span>,
    },
    {
      key: 'entry', label: 'Entry', align: 'right',
      render: (s) => <span className="font-mono">${formatPrice(s.entry_price)}</span>,
    },
    {
      key: 'sl', label: 'SL', align: 'right',
      render: (s) => <span className="font-mono text-red-400">${formatPrice(s.stop_loss)}</span>,
    },
    {
      key: 'tp1', label: 'TP1', align: 'right',
      render: (s) => <span className="font-mono text-green-400">${formatPrice(s.take_profit_1)}</span>,
    },
    {
      key: 'rr', label: 'R:R', align: 'right',
      render: (s) => `1:${s.risk_reward?.toFixed(1)}`,
    },
    {
      key: 'generated', label: 'Generated', align: 'right',
      render: (s) => <span className="text-gray-500">{formatDate(s.generated_at)}</span>,
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={signals}
      keyExtractor={(s) => s.id}
      isLoading={isLoading}
      emptyMessage="No active signals"
    />
  );
}
