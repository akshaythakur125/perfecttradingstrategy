import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Card, CardTitle } from '../common/Card';

interface MonthlyPerformanceChartProps {
  data: { month: string; pnl: number }[];
  height?: number;
}

export function MonthlyPerformanceChart({ data, height = 250 }: MonthlyPerformanceChartProps) {
  if (data.length === 0) return null;

  return (
    <Card>
      <CardTitle className="text-sm font-semibold text-gray-400 mb-3">Monthly Performance</CardTitle>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data}>
          <XAxis dataKey="month" tick={{ fill: '#666', fontSize: 10 }} />
          <YAxis hide />
          <Tooltip contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: '8px', color: '#999' }} />
          <Bar dataKey="pnl" fill="#22c55e" />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
