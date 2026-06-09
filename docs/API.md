# API Documentation

Base URL: `/api/v1`

## Authentication

All endpoints except `/health` require a Bearer token in the `Authorization` header.

### POST /auth/register

Create a new user account.

**Request:**
```json
{
  "username": "trader1",
  "email": "trader1@example.com",
  "password": "securePass123"
}
```

**Response (201):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### POST /auth/login

Authenticate and receive a JWT token.

**Request:**
```json
{
  "username": "trader1",
  "password": "securePass123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

## Signals

### GET /signals/

List signals with optional filters.

**Query Parameters:**
- `limit` (int, default 20): Max results
- `direction` (string, optional): "LONG" or "SHORT"
- `min_confidence` (float, optional): Minimum confidence score (0-100)

**Response:**
```json
[
  {
    "id": "uuid",
    "symbol": "BTCUSDT",
    "exchange": "BINANCE",
    "direction": "LONG",
    "confidence_score": 88.5,
    "entry_price": 50000.0,
    "stop_loss": 49200.0,
    "take_profit_1": 51200.0,
    "take_profit_2": 52400.0,
    "take_profit_3": 54000.0,
    "risk_reward": 3.0,
    "trend_direction": "BULLISH",
    "market_regime": "STRONG_BULL",
    "aoi_type": "DEMAND",
    "aoi_score": 85.0,
    "structure_score": 90.0,
    "volume_score": 75.0,
    "rsi_score": 80.0,
    "reasons": ["4H Trend: BULLISH", "AOI: DEMAND at $49500-$49800"],
    "generated_at": "2024-01-01T00:00:00"
  }
]
```

### GET /signals/active

Get all active (unexpired) signals, ordered by confidence descending.

### GET /signals/{id}

Get a specific signal by UUID.

## Trades

### GET /trades/

List trades with optional filters.

**Query Parameters:**
- `limit` (int, default 50)
- `status` (string, optional): "PENDING", "ACTIVE", "CLOSED", "CANCELLED"
- `symbol` (string, optional): Filter by symbol

### GET /trades/open

Get all currently open (ACTIVE) trades.

### GET /trades/{id}

Get a specific trade by UUID.

## Backtest

### POST /backtest/run

Run a backtest for a symbol.

**Request:**
```json
{
  "symbol": "BTCUSDT",
  "exchange": "BINANCE",
  "initial_capital": 10000.0
}
```

**Response:**
```json
{
  "id": "uuid",
  "symbol": "BTCUSDT",
  "total_trades": 45,
  "winning_trades": 27,
  "losing_trades": 18,
  "win_rate": 60.0,
  "profit_factor": 2.5,
  "sharpe_ratio": 1.8,
  "sortino_ratio": 2.1,
  "max_drawdown": 12.5,
  "cagr": 45.2,
  "average_rr": 2.8,
  "equity_curve": [10000, 10050, ...],
  "monthly_performance": {"2024-01": 500, "2024-02": -200},
  "created_at": "2024-01-01T00:00:00"
}
```

### GET /backtest/history

List recent backtest runs.

**Query Parameters:**
- `limit` (int, default 20)
- `symbol` (string, optional): Filter by symbol

### GET /backtest/{id}

Get a specific backtest result by UUID.

## Risk

### GET /risk/metrics

Get current risk metrics.

**Response:**
```json
{
  "daily_pnl": 150.50,
  "daily_pnl_percent": 1.5,
  "weekly_pnl": 450.00,
  "weekly_pnl_percent": 4.5,
  "open_positions": 2,
  "max_open_positions": 3,
  "daily_loss_limit_hit": false,
  "weekly_loss_limit_hit": false,
  "current_risk_per_trade": 0.01,
  "account_balance": 10000.0
}
```

## Scanner

### GET /scanner/scan

Scan top pairs for trading signals.

**Query Parameters:**
- `exchange` (string, default "BINANCE"): Exchange to scan
- `limit` (int, default 30): Number of top pairs to scan

**Response:**
```json
{
  "scanned_pairs": 30,
  "signals_found": 3,
  "signals": [...],
  "generated_at": "2024-01-01T00:00:00"
}
```

### GET /scanner/pairs

Get available USDT trading pairs.

**Query Parameters:**
- `exchange` (string, default "BINANCE")

## WebSocket

### WS /ws/scanner

Real-time scanner WebSocket endpoint.

**Send:**
```json
{
  "exchange": "BINANCE"
}
```

**Receive:**
```json
{
  "type": "scan_results",
  "data": [...]
}
```

## Health

### GET /health

**Response:**
```json
{
  "status": "ok",
  "service": "PerfectTradingStrategy",
  "version": "2.0.0"
}
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common status codes:
- `400` Bad Request — Invalid parameters
- `401` Unauthorized — Missing or invalid token
- `403` Forbidden — Account deactivated
- `404` Not Found — Resource not found
- `409` Conflict — Username already exists
- `429` Too Many Requests — Rate limit exceeded
- `500` Internal Server Error
