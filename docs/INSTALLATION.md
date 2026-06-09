# Installation Guide

## Prerequisites

- **Python 3.12+** — [Download](https://www.python.org/downloads/)
- **Node.js 18+** — [Download](https://nodejs.org/)
- **PostgreSQL 16** — [Download](https://www.postgresql.org/download/) (or use Docker)
- **Redis 7** — [Download](https://redis.io/download/) (or use Docker)

## Option 1: Docker (Recommended)

### 1. Prerequisites
- Docker Desktop 24+
- Docker Compose 2.20+

### 2. Quick Start

```bash
# Clone the repository
git clone https://github.com/akshaythakur125/perfecttradingstrategy.git
cd perfecttradingstrategy

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose -f docker/docker-compose.yml up --build
```

This starts:
- PostgreSQL 16 on port 5432
- Redis 7 on port 6379
- Backend API on port 8000

The frontend needs to be run separately:

```bash
cd frontend
npm install
npm run dev
```

## Option 2: Manual Installation

### Backend Setup

```bash
# 1. Clone the repo
git clone https://github.com/akshaythakur125/perfecttradingstrategy.git
cd perfecttradingstrategy/backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp ../.env.example ../.env
# Edit ../.env with your settings

# 5. Set up PostgreSQL database
createdb perfecttrading
# Or via psql: CREATE DATABASE perfecttrading;

# 6. Run database migrations (tables created on startup)
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
# 1. Navigate to frontend
cd perfecttradingstrategy/frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev  # Runs on http://localhost:3000
```

## Configuration

### Required Settings

1. **JWT_SECRET**: Generate a strong random key:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Exchange API Keys**: Get from your exchange account:
   - Binance: [API Management](https://www.binance.com/en/support/faq/how-to-create-api-keys-on-binance-360002502072)
   - OKX: [API Management](https://www.okx.com/account/my-api)

3. **Database URL**: Update DATABASE_URL if using non-default credentials:
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@host:5432/perfecttrading
   ```

### Environment Variables File

Create `.env` in the project root:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/perfecttrading

# Redis
REDIS_URL=redis://localhost:6379/0

# Exchange APIs
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret
BINANCE_TESTNET=true

OKX_API_KEY=your_okx_api_key
OKX_SECRET_KEY=your_okx_secret
OKX_PASSPHRASE=your_okx_passphrase
OKX_TESTNET=true

# JWT
JWT_SECRET=your-strong-random-secret-at-least-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Risk Management
MAX_OPEN_POSITIONS=3
RISK_PER_TRADE=0.01
DAILY_LOSS_LIMIT=0.03
WEEKLY_LOSS_LIMIT=0.08
MIN_RISK_REWARD=3.0

# Scanner
SCANNER_SCAN_INTERVAL=60
```

## Verifying Installation

```bash
# 1. Health check
curl http://localhost:8000/health
# Response: {"status":"ok","service":"PerfectTradingStrategy","version":"2.0.0"}

# 2. Register a test user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"testPass123"}'

# 3. Run tests
cd backend && pytest tests/ -v
```

## Troubleshooting

### Database Connection Error
```
Error: connection to server on socket "/tmp/.s.PGSQL.5432" failed
```
Ensure PostgreSQL is running: `pg_isready`

### PORT Already in Use
```bash
# Check what's running on port 8000
lsof -i :8000

# Change backend port
uvicorn main:app --port 8001
```

### Module Not Found
```bash
# Ensure virtual environment is activated and dependencies installed
pip install -r requirements.txt --upgrade
```
