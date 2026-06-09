import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../utils/helpers';

interface LoadingSpinnerProps {
  size?: number;
  className?: string;
  text?: string;
}

export function LoadingSpinner({ size = 24, className, text }: LoadingSpinnerProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12', className)}>
      <Loader2 size={size} className="animate-spin text-blue-400 mb-3" />
      {text && <p className="text-sm text-gray-500">{text}</p>}
    </div>
  );
}
