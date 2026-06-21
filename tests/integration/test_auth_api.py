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
