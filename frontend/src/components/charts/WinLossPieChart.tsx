import React from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { Card, CardTitle } from '../common/Card';

interface WinLossPieChartProps {
  wins: number;
  losses: number;
  height?: number;
}

const COLORS = ['#22c55e', '#ef4444'];

export function WinLossPieChart({ wins, losses, height = 300 }: WinLossPieChartProps) {
  const data = [
    { name: 'Wins', value: wins },
    { name: 'Losses', value: losses },
  ];

  if (wins === 0 && losses === 0) return null;

  return (
    <Card>
      <CardTitle className="text-sm font-semibold text-gray-400 mb-3">Win / Loss Distribution</CardTitle>
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            dataKey="value"
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
          >
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index]} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: '8px', color: '#999' }} />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  );
}
