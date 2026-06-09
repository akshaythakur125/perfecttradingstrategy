import React from 'react';
import { cn } from '../../utils/helpers';

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: React.ElementType;
  color?: string;
  trend?: 'up' | 'down' | 'neutral';
  className?: string;
}

export function StatCard({ label, value, icon: Icon, color, trend, className }: StatCardProps) {
  return (
    <div className={cn('p-4 bg-gray-900 rounded-xl border border-gray-800', className)}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-gray-500">{label}</span>
        {Icon && <Icon size={16} className={color || 'text-gray-400'} />}
      </div>
      <div className={cn('text-xl font-bold', color || 'text-white')}>{value}</div>
      {trend && (
        <span className={cn(
          'text-xs',
          trend === 'up' && 'text-green-400',
          trend === 'down' && 'text-red-400',
          trend === 'neutral' && 'text-gray-400',
        )}>
          {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
        </span>
      )}
    </div>
  );
}
