import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { BacktestResult } from '../../utils/types';
import { Card, CardTitle } from '../common/Card';

interface BacktestChartsProps {
  result: BacktestResult;
}

export function BacktestCharts({ result }: BacktestChartsProps) {
  const equityData = result.equity_curve?.map((val, i) => ({ bar: i, equity: val })) || [];
  const monthlyData = result.monthly_performance
    ? Object.entries(result.monthly_performance).map(([month, pnl]) => ({ month, pnl }))
    : [];

  const tooltipStyle = { background: '#111', border: '1px solid #333', borderRadius: '8px', color: '#999' };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {equityData.length > 0 && (
        <Card>
          <CardTitle className="text-sm font-semibold text-gray-400 mb-3">Equity Curve</CardTitle>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={equityData}>
              <XAxis dataKey="bar" hide />
              <YAxis domain={['auto', 'auto']} hide />
              <Tooltip contentStyle={tooltipStyle} />
              <Line type="monotone" dataKey="equity" stroke="#3b82f6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}
      {monthlyData.length > 0 && (
        <Card>
          <CardTitle className="text-sm font-semibold text-gray-400 mb-3">Monthly Performance</CardTitle>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={monthlyData}>
              <XAxis dataKey="month" tick={{ fill: '#666', fontSize: 10 }} />
              <YAxis hide />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="pnl" fill="#22c55e" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  );
}
