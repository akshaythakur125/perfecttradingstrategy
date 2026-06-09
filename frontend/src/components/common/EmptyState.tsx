import React from 'react';
import { cn } from '../../utils/helpers';

interface EmptyStateProps {
  icon: React.ElementType;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('text-center py-16', className)}>
      <Icon size={48} className="mx-auto mb-4 text-gray-600" />
      <h3 className="text-lg font-medium text-gray-400 mb-1">{title}</h3>
      {description && <p className="text-sm text-gray-500 mb-4">{description}</p>}
      {action && <div>{action}</div>}
    </div>
  );
}
