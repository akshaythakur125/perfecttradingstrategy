# PerfectTradingStrategy

**Production-ready cryptocurrency futures trading platform** with multi-timeframe technical analysis, automated signal generation, backtesting, and risk management.

## Features

- **Multi-Timeframe Analysis** — Combines 4H (trend/regime) and 15M (entry) timeframes for high-probability setups
- **Market Structure Analysis** — Swing highs/lows, Break of Structure (BOS), Change of Character (CHOCH), trend classification
- **AOI Detection** — Supply/demand zones, order blocks, fair value gaps (FVGs), liquidity pools, equal highs/lows, wick rejections
- **Signal Engine** — Weighted multi-factor scoring (structure 25%, AOI 25%, volume 15%, RSI 10%, OBV 10%, OI 10%, funding 5%)
- **Backtesting Engine** — Walk-forward simulation with TP1/TP2/TP3 partial exits, break-even logic, trailing stops
- **Risk Manager** — Position sizing, daily/weekly loss limits, ATR-based stops, R:R filtering
- **Scanner** — Concurrent pair scanning across Binance and OKX futures
- **WebSocket Dashboard** — Real-time signal updates
- **REST API** — Full CRUD for signals, trades, backtests, user settings
- **JWT Authentication** — Secure user registration and login

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (React 18)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ Scanner  │ │ Signals  │ │ Backtest / Analytics  │ │
│  └────┬─────┘ └────┬─────┘ └──────────┬───────────┘ │
│       └────────────┼──────────────────┘              │
│                    │ HTTP / WebSocket                 │
└────────────────────┼─────────────────────────────────┘
                     │
┌────────────────────┼─────────────────────────────────┐
│           Backend (FastAPI + Python 3.12)             │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ Routers  │ │ Engines  │ │ Services / Auth      │ │
│  └────┬─────┘ └────┬─────┘ └──────────┬───────────┘ │
│       │            │                   │              │
│  ┌────┴────────────┴───────────────────┴──────────┐ │
│  │            SQLAlchemy Async ORM                 │ │
│  └────────────────────┬───────────────────────────┘ │
└───────────────────────┼─────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   PostgreSQL          Redis         Exchange APIs
   (Primary DB)      (Cache)     (Binance / OKX)
```

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **Database** | PostgreSQL 16 (async), SQLAlchemy 2.0, asyncpg |
| **Cache** | Redis 7 |
| **Auth** | JWT (HS256), bcrypt |
| **Data** | NumPy, Pandas, aiohttp |
| **Testing** | pytest, pytest-asyncio, httpx |
| **Frontend** | React 18, TypeScript, Vite |
| **Styling** | Tailwind CSS 3.4 |
| **Charts** | Recharts, lightweight-charts |
| **State** | TanStack React Query |
| **Containerization** | Docker, Docker Compose |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 16 (or use Docker)

### 1. Clone & Install Backend

```bash
git clone https://github.com/akshaythakur125/perfecttradingstrategy.git
cd perfecttradingstrategy

cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

### 3. Install & Run Frontend

```bash
cd frontend
npm install
npm run dev  # Runs on http://localhost:3000
```

### 4. Run Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 5. Using Docker (recommended)

```bash
docker-compose -f docker/docker-compose.yml up --build
```

## Configuration

Key environment variables (see `.env.example`):

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `JWT_SECRET` | JWT signing key (min 16 chars) | `change-me` |
| `BINANCE_API_KEY` | Binance Futures API key | — |
| `BINANCE_SECRET_KEY` | Binance Futures secret key | — |
| `OKX_API_KEY` | OKX API key | — |
| `OKX_SECRET_KEY` | OKX secret key | — |
| `RISK_PER_TRADE` | Risk per trade (decimal) | `0.01` (1%) |
| `MAX_OPEN_POSITIONS` | Max concurrent positions | `3` |
| `DAILY_LOSS_LIMIT` | Daily loss limit (decimal) | `0.03` (3%) |
| `MIN_RISK_REWARD` | Minimum risk/reward ratio | `3.0` |

## API Overview

All endpoints are under `/api/v1` and require JWT authentication (except `/health`).

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/auth/register` | POST | Create account |
| `/auth/login` | POST | Sign in |
| `/signals/` | GET | List signals |
| `/signals/active` | GET | Active signals |
| `/trades/` | GET | List trades |
| `/trades/open` | GET | Open positions |
| `/backtest/run` | POST | Run backtest |
| `/backtest/history` | GET | Backtest history |
| `/risk/metrics` | GET | Risk metrics |
| `/scanner/scan` | GET | Scan markets |
| `/ws/scanner` | WS | Real-time scanner |

## Testing

```bash
# Backend tests
cd backend
pytest tests/ -v

# With coverage
pytest tests/ --cov=engines --cov=routers --cov=services --cov=config --cov-report=term-missing
```

## License

MIT
