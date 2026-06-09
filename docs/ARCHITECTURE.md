# Architecture Guide

## Project Structure

```
perfecttradingstrategy/
├── backend/
│   ├── main.py                    # FastAPI application entry point
│   ├── config/
│   │   └── settings.py            # Pydantic-settings configuration
│   ├── database/
│   │   ├── __init__.py            # SQLAlchemy Base
│   │   └── session.py            # Async engine and session factory
│   ├── models/
│   │   └── models.py             # 8 ORM models (User, Trade, Signal, etc.)
│   ├── schemas/
│   │   └── schemas.py            # Pydantic request/response schemas
│   ├── engines/
│   │   ├── indicators.py         # RSI, EMA, ATR, OBV, volume analysis
│   │   ├── market_structure.py   # Swing highs/lows, BOS, CHOCH, regime
│   │   ├── aoi_detection.py      # Supply/demand, order blocks, FVGs, liquidity
│   │   ├── signal_engine.py      # Multi-factor signal scoring
│   │   ├── scanner.py            # Concurrent pair scanner
│   │   ├── risk_manager.py       # Position sizing, loss limits
│   │   ├── backtest_engine.py    # Walk-forward backtesting with partial exits
│   │   ├── data_collector.py     # Exchange data facade
│   │   └── exchange_clients.py   # Binance/OKX REST clients
│   ├── routers/
│   │   ├── auth.py               # Registration and login
│   │   ├── signals.py            # Signal CRUD
│   │   ├── trades.py             # Trade CRUD
│   │   ├── backtest.py           # Backtest execution and history
│   │   ├── risk.py               # Risk metrics
│   │   ├── scanner.py            # Market scanning
│   │   └── websocket.py          # WebSocket manager
│   ├── services/
│   │   └── auth.py               # Password hashing, JWT handling
│   ├── middleware/
│   │   └── rate_limit.py         # IP-based rate limiting
│   └── utils/
│       ├── logger.py             # Logging configuration
│       └── security.py           # Input sanitization, validation
├── frontend/
│   ├── src/
│   │   ├── App.tsx               # Router and query client setup
│   │   ├── main.tsx              # React entry point
│   │   ├── pages/                # 8 page components
│   │   ├── components/           # Reusable UI components
│   │   ├── hooks/                # Custom hooks (useWebSocket)
│   │   ├── services/             # Axios API client
│   │   └── utils/                # Types and helper functions
│   ├── vite.config.ts
│   └── tailwind.config.js
├── docker/
│   ├── Dockerfile                # Backend container
│   └── docker-compose.yml        # PostgreSQL + Redis + Backend
├── docs/                         # Documentation
├── scripts/                      # Utility scripts
├── k8s/                          # Kubernetes manifests (planned)
└── tests/
    └── test_engines.py           # Engine-level pytest tests
```

## Data Flow

### Signal Generation Pipeline

```
Exchange API → DataCollector → Indicators → Market Structure Analysis
                                                    ↓
                                              AOI Detection
                                                    ↓
                                             Signal Engine
                                                    ↓
                                          Score ≥ 80% & R:R ≥ 3
                                                    ↓
                                              Store Signal
                                                    ↓
                                         WebSocket / REST → Frontend
```

### Backtesting Pipeline

```
Exchange API → Historical Data → compute_all_indicators()
                                       ↓
                              analyze_market_structure()
                                       ↓
                                detect_all_aois()
                                       ↓
                              evaluate_long/short_setup()
                                       ↓
                              Walk-forward loop (4H bars)
                                       ↓
                              Entry validation + Position sizing
                                       ↓
                              15M bar simulation (up to 96 bars)
                                       ↓
                              TP1 (50%) → BE → TP2 (30%) → Trail → TP3 (20%)
                                       ↓
                         Metrics: Sharpe, Sortino, DD, CAGR, etc.
```

## Database Schema

8 tables with UUID primary keys:
- **users** — Account management
- **user_settings** — Per-user risk preferences
- **trades** — Trade records with full entry/exit details
- **signals** — Generated trading signals with component scores
- **backtests** — Backtest results with performance metrics
- **market_data** — OHLCV + OI + funding rate storage
- **aois** — Detected areas of interest
- **trade_journal** — Trade journaling

## Signal Scoring Weights

| Factor | Weight | Description |
|---|---|---|
| Market Structure | 25% | Trend, regime, BOS alignment |
| AOI Strength | 25% | Zone type, reactions, volume confirmation |
| Volume | 15% | Volume spike relative to moving average |
| RSI | 10% | Oversold/overbought positioning |
| OBV | 10% | Volume-flow confirmation |
| Open Interest | 10% | OI change direction |
| Funding Rate | 5% | Funding rate positioning |

## Risk Management

- **Position Sizing**: Fixed percentage risk (default 1%)
- **Leverage**: Dynamic (max 10x, capped at 50% margin usage)
- **Daily Loss Limit**: Default 3% of account
- **Weekly Loss Limit**: Default 8% of account
- **Min R:R**: Default 1:3
- **ATR Stops**: 2x ATR for initial stop
- **Partial Exits**: TP1 50%, TP2 30%, TP3 20%
- **Break-Even**: SL moved to entry after TP1
- **Trailing Stop**: Activated after TP2
