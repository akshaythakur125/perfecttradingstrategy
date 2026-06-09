import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from database import Base
from database.session import get_db
from main import app
from models.models import User
from services.auth import hash_password, create_access_token


@pytest_asyncio.fixture
async def async_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with async_session() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def auth_token(async_client):
    response = await async_client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testPass123",
    })
    assert response.status_code == 201
    return response.json()["access_token"]


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_check(self, async_client):
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data


class TestAuth:
    @pytest.mark.asyncio
    async def test_register(self, async_client):
        response = await async_client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "StrongPass1",
        })
        assert response.status_code == 201
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    async def test_register_duplicate(self, async_client):
        await async_client.post("/api/v1/auth/register", json={
            "username": "dupuser",
            "email": "dup@example.com",
            "password": "StrongPass1",
        })
        response = await async_client.post("/api/v1/auth/register", json={
            "username": "dupuser",
            "email": "dup2@example.com",
            "password": "StrongPass1",
        })
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_weak_password(self, async_client):
        response = await async_client.post("/api/v1/auth/register", json={
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "short",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login(self, async_client):
        await async_client.post("/api/v1/auth/register", json={
            "username": "loginuser",
            "email": "login@example.com",
            "password": "loginPass1",
        })
        response = await async_client.post("/api/v1/auth/login", json={
            "username": "loginuser",
            "password": "loginPass1",
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client):
        response = await async_client.post("/api/v1/auth/login", json={
            "username": "nonexistent",
            "password": "wrong",
        })
        assert response.status_code == 401


class TestSignals:
    @pytest.mark.asyncio
    async def test_get_signals_requires_auth(self, async_client):
        response = await async_client.get("/api/v1/signals/")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_signals_authenticated(self, async_client, auth_token):
        response = await async_client.get(
            "/api/v1/signals/",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_active_signals(self, async_client, auth_token):
        response = await async_client.get(
            "/api/v1/signals/active",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200


class TestTrades:
    @pytest.mark.asyncio
    async def test_get_trades(self, async_client, auth_token):
        response = await async_client.get(
            "/api/v1/trades/",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_open_trades(self, async_client, auth_token):
        response = await async_client.get(
            "/api/v1/trades/open",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200


class TestRisk:
    @pytest.mark.asyncio
    async def test_get_risk_metrics(self, async_client, auth_token):
        response = await async_client.get(
            "/api/v1/risk/metrics",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "daily_pnl" in data
        assert "weekly_pnl" in data
        assert "open_positions" in data


class TestScanner:
    @pytest.mark.asyncio
    async def test_get_pairs(self, async_client, auth_token):
        response = await async_client.get(
            "/api/v1/scanner/pairs?exchange=BINANCE",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code in (200, 503)


class TestBacktest:
    @pytest.mark.asyncio
    async def test_backtest_history(self, async_client, auth_token):
        response = await async_client.get(
            "/api/v1/backtest/history",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
