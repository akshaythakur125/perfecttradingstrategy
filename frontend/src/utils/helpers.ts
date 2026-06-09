import { clsx, type ClassValue } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatPrice(price: number, decimals = 2): string {
  return price.toFixed(decimals);
}

export function formatPercent(value: number, decimals = 2): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}%`;
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function getConfidenceColor(score: number): string {
  if (score >= 90) return 'text-emerald-400';
  if (score >= 80) return 'text-green-400';
  if (score >= 70) return 'text-yellow-400';
  return 'text-gray-400';
}

export function getConfidenceBg(score: number): string {
  if (score >= 90) return 'bg-emerald-500/20 border-emerald-500/40';
  if (score >= 80) return 'bg-green-500/20 border-green-500/40';
  if (score >= 70) return 'bg-yellow-500/20 border-yellow-500/40';
  return 'bg-gray-500/20 border-gray-500/40';
}

export function getDirectionColor(direction: string): string {
  return direction === 'LONG' ? 'text-green-400' : 'text-red-400';
}
