from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database.session import init_db
from routers import auth, signals, trades, backtest, risk, scanner, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="PerfectTradingStrategy API",
    description="Cryptocurrency Futures Trading Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "https://*.perfecttrading.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(signals.router)
app.include_router(trades.router)
app.include_router(backtest.router)
app.include_router(risk.router)
app.include_router(scanner.router)
app.include_router(websocket.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "PerfectTradingStrategy"}
