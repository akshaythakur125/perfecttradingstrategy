export interface Signal {
  id: string;
  symbol: string;
  exchange: string;
  direction: 'LONG' | 'SHORT';
  confidence_score: number;
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2?: number;
  take_profit_3?: number;
  risk_reward: number;
  trend_direction: string;
  market_regime?: string;
  aoi_type?: string;
  aoi_price_low?: number;
  aoi_price_high?: number;
  reasons?: string[];
  generated_at: string;
}

export interface Trade {
  id: string;
  symbol: string;
  exchange: string;
  direction: 'LONG' | 'SHORT';
  status: string;
  entry_price: number;
  stop_loss: number;
  take_profit_1?: number;
  take_profit_2?: number;
  take_profit_3?: number;
  position_size?: number;
  dollar_risk?: number;
  risk_reward?: number;
  pnl?: number;
  pnl_percent?: number;
  confidence_score?: number;
  entry_time?: string;
  exit_time?: string;
  created_at: string;
}

export interface BacktestResult {
  id: string;
  symbol: string;
  exchange: string;
  total_trades?: number;
  win_rate?: number;
  profit_factor?: number;
  sharpe_ratio?: number;
  sortino_ratio?: number;
  max_drawdown?: number;
  cagr?: number;
  average_rr?: number;
  average_holding_time?: number;
  total_pnl?: number;
  initial_capital?: number;
  final_capital?: number;
  equity_curve?: number[];
  monthly_performance?: Record<string, number>;
  created_at: string;
}

export interface RiskMetrics {
  daily_pnl: number;
  daily_pnl_percent: number;
  weekly_pnl: number;
  weekly_pnl_percent: number;
  open_positions: number;
  max_open_positions: number;
  daily_loss_limit_hit: boolean;
  weekly_loss_limit_hit: boolean;
  current_risk_per_trade: number;
  account_balance?: number;
}

export interface ScannerResult {
  scanned_pairs: number;
  signals_found: number;
  signals: Signal[];
  generated_at: string;
}
