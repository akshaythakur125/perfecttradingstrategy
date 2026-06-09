import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Card, CardTitle } from '../common/Card';

interface EquityCurveChartProps {
  data: { bar: number; equity: number }[];
  height?: number;
}

export function EquityCurveChart({ data, height = 250 }: EquityCurveChartProps) {
  if (data.length === 0) return null;

  return (
    <Card>
      <CardTitle className="text-sm font-semibold text-gray-400 mb-3">Equity Curve</CardTitle>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data}>
          <XAxis dataKey="bar" hide />
          <YAxis domain={['auto', 'auto']} hide />
          <Tooltip contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: '8px', color: '#999' }} />
          <Line type="monotone" dataKey="equity" stroke="#3b82f6" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
