"""Integration tests for auth and user-scoped protected APIs."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.qlib_research.app.api.routes import auth, broker, portfolio
from src.qlib_research.app.db import get_db
from src.qlib_research.app.models.database import Base


@pytest.fixture
def client():
    """Create a test client with isolated SQLite database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False,
    )
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(auth.router, prefix="/api/auth")
    app.include_router(broker.router, prefix="/api/broker")
    app.include_router(portfolio.router, prefix="/api/portfolio")

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _signup_and_login(client: TestClient, username: str, email: str, password: str) -> str:
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "username": username,
            "email": email,
            "password": password,
            "full_name": f"{username} test",
        },
    )
    assert signup_response.status_code == 200

    login_response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestAuthAPI:
    def test_signup_login_and_me_flow(self, client: TestClient):
        token = _signup_and_login(
            client=client,
            username="alice",
            email="alice@example.com",
            password="password123",
        )

        me_response = client.get("/api/auth/me", headers=_auth_headers(token))
        assert me_response.status_code == 200
        payload = me_response.json()
        assert payload["username"] == "alice"
        assert payload["email"] == "alice@example.com"
        assert payload["is_active"] is True

    def test_protected_endpoint_requires_token(self, client: TestClient):
        me_response = client.get("/api/auth/me")
        assert me_response.status_code == 401

        portfolio_response = client.get("/api/portfolio/overview")
        assert portfolio_response.status_code == 401

    def test_cross_user_isolation_for_orders_and_portfolio(self, client: TestClient):
        token_a = _signup_and_login(
            client=client,
            username="trader_a",
            email="trader_a@example.com",
            password="password123",
        )
        token_b = _signup_and_login(
            client=client,
            username="trader_b",
            email="trader_b@example.com",
            password="password123",
        )

        create_order_response = client.post(
            "/api/broker/orders",
            headers=_auth_headers(token_a),
            json={
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 10,
                "order_type": "market",
            },
        )
        assert create_order_response.status_code == 200
        order_id = create_order_response.json()["order_id"]

        user_a_orders = client.get("/api/broker/orders", headers=_auth_headers(token_a))
        assert user_a_orders.status_code == 200
        assert len(user_a_orders.json()) == 1

        user_b_orders = client.get("/api/broker/orders", headers=_auth_headers(token_b))
        assert user_b_orders.status_code == 200
        assert user_b_orders.json() == []

        user_b_order_lookup = client.get(
            f"/api/broker/orders/{order_id}",
            headers=_auth_headers(token_b),
        )
        assert user_b_order_lookup.status_code == 404

        user_a_portfolio = client.get("/api/portfolio/overview", headers=_auth_headers(token_a))
        user_b_portfolio = client.get("/api/portfolio/overview", headers=_auth_headers(token_b))
        assert user_a_portfolio.status_code == 200
        assert user_b_portfolio.status_code == 200
        assert user_a_portfolio.json()["open_positions"] == 1
        assert user_b_portfolio.json()["open_positions"] == 0

    def test_live_adapter_endpoints_require_auth_and_return_snapshot(self, client: TestClient):
        unauthorized = client.get("/api/broker/live/status")
        assert unauthorized.status_code == 401

        token = _signup_and_login(
            client=client,
            username="live_check_user",
            email="live_check_user@example.com",
            password="password123",
        )

        status_response = client.get("/api/broker/live/status", headers=_auth_headers(token))
        assert status_response.status_code == 200
        status_payload = status_response.json()
        assert "adapter_mode" in status_payload
        assert "read_only" in status_payload
        assert "execution_enabled" in status_payload

        account_response = client.get("/api/broker/live/account", headers=_auth_headers(token))
        assert account_response.status_code == 200
        account_payload = account_response.json()
        assert "portfolio_value" in account_payload
        assert "cash" in account_payload
        assert "synced_at" in account_payload

    def test_live_reconciliation_respects_feature_flag(self, client: TestClient, monkeypatch):
        token = _signup_and_login(
            client=client,
            username="recon_user",
            email="recon_user@example.com",
            password="password123",
        )
        headers = _auth_headers(token)

        monkeypatch.setenv("PHASE3_ENABLE_BROKER_RECONCILIATION", "false")
        disabled_response = client.get("/api/broker/live/reconciliation", headers=headers)
        assert disabled_response.status_code == 503

        monkeypatch.setenv("PHASE3_ENABLE_BROKER_RECONCILIATION", "true")
        enabled_response = client.get("/api/broker/live/reconciliation", headers=headers)
        assert enabled_response.status_code == 200
        payload = enabled_response.json()
        assert "status" in payload
        assert "live" in payload
        assert "alerts" in payload

    def test_pretrade_risk_guardrail_rejects_oversized_order(self, client: TestClient, monkeypatch):
        token = _signup_and_login(
            client=client,
            username="risk_user",
            email="risk_user@example.com",
            password="password123",
        )
        monkeypatch.setenv("PHASE3_MAX_TRADE_NOTIONAL", "1000")

        response = client.post(
            "/api/broker/orders",
            headers=_auth_headers(token),
            json={
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 20,
                "order_type": "market",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "rejected"
        assert payload["rejected_reason"] is not None

    def test_strategy_automation_requires_flag_and_confirmation(self, client: TestClient, monkeypatch):
        token = _signup_and_login(
            client=client,
            username="auto_user",
            email="auto_user@example.com",
            password="password123",
        )
        headers = _auth_headers(token)

        monkeypatch.setenv("PHASE3_ENABLE_STRATEGY_AUTOMATION", "false")
        disabled = client.post(
            "/api/broker/automation/proposals",
            headers=headers,
            json={
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 5,
                "confidence": 0.75,
                "rationale": "Momentum signal",
            },
        )
        assert disabled.status_code == 503

        monkeypatch.setenv("PHASE3_ENABLE_STRATEGY_AUTOMATION", "true")
        proposal_response = client.post(
            "/api/broker/automation/proposals",
            headers=headers,
            json={
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 5,
                "confidence": 0.75,
                "rationale": "Momentum signal",
            },
        )
        assert proposal_response.status_code == 200
        proposal_id = proposal_response.json()["proposal_id"]

        rejected_execute = client.post(
            f"/api/broker/automation/proposals/{proposal_id}/execute",
            headers=headers,
            json={"current_price": 100.0},
        )
        assert rejected_execute.status_code == 400

        confirmed_execute = client.post(
            f"/api/broker/automation/proposals/{proposal_id}/execute",
            headers=headers,
            json={"confirmation_text": "CONFIRM", "current_price": 100.0},
        )
        assert confirmed_execute.status_code == 200
        assert confirmed_execute.json()["order"]["status"] in {"filled", "pending", "rejected"}
