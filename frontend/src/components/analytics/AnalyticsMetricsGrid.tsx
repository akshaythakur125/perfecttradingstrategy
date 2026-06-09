import React from 'react';
import { StatCard } from '../common/StatCard';

interface AnalyticsMetricsGridProps {
  metrics: { label: string; value: string; color?: string; trend?: 'up' | 'down' }[];
}

export function AnalyticsMetricsGrid({ metrics }: AnalyticsMetricsGridProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
      {metrics.map((m) => (
        <StatCard key={m.label} label={m.label} value={m.value} color={m.color} trend={m.trend} />
      ))}
    </div>
  );
}
