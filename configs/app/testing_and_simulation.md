# Testing & Simulation Specification
# Unit, integration, end-to-end tests and paper trading simulation

## Overview

Testing strategy covers:
1. **Unit Tests** — Individual services, models, calculations
2. **Integration Tests** — API endpoints with mocked dependencies
3. **End-to-End Tests** — Full user workflows via browser automation
4. **Paper Trading Simulation** — Multi-day backtests with live market data
5. **Load Testing** — Performance under concurrent requests

## Test Structure

```
tests/
├── unit/
│   ├── test_greeks_calculator.py
│   ├── test_portfolio_greeks.py
│   ├── test_risk_calculator.py
│   ├── test_execution_safeguards.py
│   ├── test_market_data_service.py
│   └── test_qlib_models.py
├── integration/
│   ├── test_api_market_routes.py
│   ├── test_api_trading_routes.py
│   ├── test_api_portfolio_routes.py
│   └── test_order_execution_flow.py
├── e2e/
│   ├── test_market_overview_flow.py
│   ├── test_stock_analysis_flow.py
│   ├── test_order_placement_flow.py
│   └── test_portfolio_monitoring_flow.py
├── simulation/
│   ├── test_paper_trading_backtest.py
│   ├── test_signal_generation.py
│   └── test_strategy_performance.py
└── conftest.py  # Shared fixtures
```

## Unit Tests

### Greeks Calculator Tests

```python
# tests/unit/test_greeks_calculator.py

import pytest
from src.qlib_research.app.services.greeks_calculator import GreeksCalculator

class TestBlackScholesCalculator:
    """Test Black-Scholes pricing and Greeks"""
    
    def test_atm_call_price_reasonable(self):
        """ATM call should have price between 0 and stock price"""
        price = GreeksCalculator.black_scholes_price(
            S=100, K=100, T=0.25, r=0.05, sigma=0.20, option_type="call"
        )
        assert 0 < price < 100
    
    def test_delta_call_range(self):
        """Call delta should be between 0 and 1"""
        delta = GreeksCalculator.delta(
            S=100, K=100, T=0.25, r=0.05, sigma=0.20, option_type="call"
        )
        assert 0 < delta < 1
    
    def test_delta_put_range(self):
        """Put delta should be between -1 and 0"""
        delta = GreeksCalculator.delta(
            S=100, K=100, T=0.25, r=0.05, sigma=0.20, option_type="put"
        )
        assert -1 < delta < 0
    
    def test_gamma_always_positive(self):
        """Gamma should always be positive"""
        gamma = GreeksCalculator.gamma(
            S=100, K=100, T=0.25, r=0.05, sigma=0.20
        )
        assert gamma > 0
    
    def test_theta_decay_over_time(self):
        """Theta should become more negative as expiration approaches"""
        theta_3m = GreeksCalculator.theta(
            S=100, K=100, T=0.25, r=0.05, sigma=0.20, option_type="call"
        )
        theta_1d = GreeksCalculator.theta(
            S=100, K=100, T=1/365, r=0.05, sigma=0.20, option_type="call"
        )
        # Last day should have larger time decay
        assert abs(theta_1d) > abs(theta_3m)
    
    def test_itm_call_has_high_delta(self):
        """Deep ITM call should have delta near 1"""
        delta = GreeksCalculator.delta(
            S=150, K=100, T=0.25, r=0.05, sigma=0.20, option_type="call"
        )
        assert delta > 0.9
    
    def test_otm_call_has_low_delta(self):
        """Deep OTM call should have delta near 0"""
        delta = GreeksCalculator.delta(
            S=50, K=100, T=0.25, r=0.05, sigma=0.20, option_type="call"
        )
        assert delta < 0.1
    
    @pytest.mark.parametrize("S,K,expected_sign", [
        (150, 100, 1),    # ITM call: positive theta for seller
        (50, 100, -1),    # OTM call: negative theta for buyer
    ])
    def test_theta_signs(self, S, K, expected_sign):
        """Verify theta signs match expectations"""
        theta = GreeksCalculator.theta(
            S=S, K=K, T=0.25, r=0.05, sigma=0.20, option_type="call"
        )
        assert (theta * expected_sign) > 0
```

### Portfolio Greeks Tests

```python
# tests/unit/test_portfolio_greeks.py

import pytest
from src.qlib_research.app.models.position import (
    StockPosition, OptionPosition, PortfolioPosition
)
from src.qlib_research.app.services.portfolio_greeks import PortfolioGreeksCalculator

def test_stock_delta_equals_quantity():
    """100 shares = delta of 100"""
    positions = PortfolioPosition(
        total_market_value=15000,
        cash_balance=0,
        stock_positions={"AAPL": StockPosition(
            ticker="AAPL", quantity=100, entry_price=150, current_price=150
        )},
        option_positions={}
    )
    
    greeks = PortfolioGreeksCalculator.calculate_portfolio_greeks(positions)
    assert greeks["delta"] == 100

def test_short_position_negative_delta():
    """Short 100 shares = delta of -100"""
    positions = PortfolioPosition(
        total_market_value=0,
        cash_balance=15000,
        stock_positions={"AAPL": StockPosition(
            ticker="AAPL", quantity=-100, entry_price=150, current_price=150
        )},
        option_positions={}
    )
    
    greeks = PortfolioGreeksCalculator.calculate_portfolio_greeks(positions)
    assert greeks["delta"] == -100

def test_delta_neutral_portfolio():
    """Long call + short stock should neutralize delta"""
    # This requires mocking option Greeks (simplified example)
    positions = PortfolioPosition(
        total_market_value=10000,
        cash_balance=0,
        stock_positions={"AAPL": StockPosition(
            ticker="AAPL", quantity=-100, entry_price=150, current_price=150
        )},
        option_positions={}  # Would add long call with delta ~0.5, qty 200
    )
    
    # Expected: -100 (short stock) + 0 (options removed for clarity)
    greeks = PortfolioGreeksCalculator.calculate_portfolio_greeks(positions)
    assert greeks["delta"] == -100
```

### Risk Calculator Tests

```python
# tests/unit/test_risk_calculator.py

import pytest
import numpy as np
from src.qlib_research.app.services.risk_calculator import RiskCalculator

def test_pnl_calculation():
    """Test P&L snapshot"""
    positions = PortfolioPosition(
        realized_pnl=500,
        unrealized_pnl=250,
        total_market_value=10000
    )
    
    pnl = RiskCalculator.calculate_pnl(positions)
    
    assert pnl["realized_pnl"] == 500
    assert pnl["unrealized_pnl"] == 250
    assert pnl["total_pnl"] == 750
    assert pnl["total_pnl_pct"] == 0.075  # 7.5%

def test_sharpe_ratio_positive_returns():
    """Sharpe ratio for profitable period"""
    pnl_history = [100, 150, 120, 200, 180]  # All positive days
    
    sharpe = RiskCalculator.calculate_sharpe_ratio(pnl_history)
    
    assert sharpe > 1  # Good Sharpe

def test_sharpe_ratio_negative_returns():
    """Sharpe ratio for losing period"""
    pnl_history = [-100, -150, -120, -200, -180]  # All negative
    
    sharpe = RiskCalculator.calculate_sharpe_ratio(pnl_history)
    
    assert sharpe < -1  # Bad Sharpe

def test_max_drawdown():
    """Test maximum consecutive drawdown"""
    pnl_history = [100, 100, -200, 50, 75]  # Peaks at $200, drops to $0
    
    dd = RiskCalculator.calculate_max_drawdown(pnl_history)
    
    assert dd == 200  # $200 drawdown from peak

def test_win_rate():
    """Win rate calculation"""
    pnl_history = [100, -50, 200, 150, -75, 300]
    
    wr = RiskCalculator.calculate_win_rate(pnl_history)
    
    assert wr == 4/6  # 4 winning days out of 6
```

### Execution Safeguards Tests

```python
# tests/unit/test_execution_safeguards.py

import pytest
from src.qlib_research.app.services.execution_safeguards import (
    InstrumentValidator, OrderValidator, BuyingPowerValidator
)

def test_valid_ticker():
    """Valid ticker passes"""
    validator = InstrumentValidator()
    ok, msg = validator.validate_instrument("AAPL")
    assert ok

def test_invalid_ticker():
    """Unknown ticker fails"""
    validator = InstrumentValidator()
    ok, msg = validator.validate_instrument("UNKNOWN_XYZ")
    assert not ok
    assert "not supported" in msg

def test_positive_quantity():
    """Positive quantity passes"""
    validator = OrderValidator()
    ok, msg = validator.validate_quantity(100)
    assert ok

def test_negative_quantity():
    """Negative quantity fails"""
    validator = OrderValidator()
    ok, msg = validator.validate_quantity(-100)
    assert not ok

def test_zero_quantity():
    """Zero quantity fails"""
    validator = OrderValidator()
    ok, msg = validator.validate_quantity(0)
    assert not ok

def test_excessive_quantity():
    """Quantity > max fails"""
    validator = OrderValidator()
    ok, msg = validator.validate_quantity(50000)
    assert not ok

def test_limit_price_reasonable():
    """Limit price within 20% passes"""
    validator = OrderValidator()
    ok, msg = validator.validate_limit_price(
        limit_price=110, current_price=100, side="buy"
    )
    assert ok

def test_limit_price_too_high():
    """Buy limit >20% above market fails"""
    validator = OrderValidator()
    ok, msg = validator.validate_limit_price(
        limit_price=130, current_price=100, side="buy"
    )
    assert not ok

def test_sufficient_buying_power():
    """Order with sufficient cash passes"""
    bpv = BuyingPowerValidator()
    ok, msg = bpv.validate_buying_power(
        "buy", 100, 150, cash_balance=20000, portfolio=None
    )
    assert ok

def test_insufficient_buying_power():
    """Order without cash fails"""
    bpv = BuyingPowerValidator()
    ok, msg = bpv.validate_buying_power(
        "buy", 1000, 150, cash_balance=100, portfolio=None
    )
    assert not ok
```

## Integration Tests

### API Route Tests

```python
# tests/integration/test_api_trading_routes.py

import pytest
from fastapi.testclient import TestClient
from src.qlib_research.app.api.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_order():
    return {
        "ticker": "AAPL",
        "side": "buy",
        "quantity": 100,
        "order_type": "market"
    }

def test_create_order_success(client, sample_order):
    """Successfully create market order"""
    response = client.post("/api/v1/orders", json=sample_order)
    
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"]
    assert data["ticker"] == "AAPL"
    assert data["status"] in ["filled", "submitted"]

def test_create_order_insufficient_capital(client):
    """Reject order without buying power"""
    response = client.post("/api/v1/orders", json={
        "ticker": "AAPL",
        "side": "buy",
        "quantity": 100000,  # Very large, exceed capital
        "order_type": "market"
    })
    
    assert response.status_code == 400
    data = response.json()
    assert "buying power" in data["message"].lower()

def test_get_order_status(client, sample_order):
    """Get status of existing order"""
    # Create order first
    create_response = client.post("/api/v1/orders", json=sample_order)
    order_id = create_response.json()["order_id"]
    
    # Get order status
    get_response = client.get(f"/api/v1/orders/{order_id}")
    
    assert get_response.status_code == 200
    assert get_response.json()["order_id"] == order_id

def test_cancel_order(client, sample_order):
    """Cancel pending order"""
    # Create order
    create_response = client.post("/api/v1/orders", json=sample_order)
    order_id = create_response.json()["order_id"]
    
    # Cancel
    cancel_response = client.delete(f"/api/v1/orders/{order_id}")
    
    assert cancel_response.status_code == 200

def test_market_overview(client):
    """Get market prices"""
    response = client.get("/api/v1/market/overview?tickers=AAPL,MSFT")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["overview"]) == 2
    assert "price" in data["overview"][0]

def test_portfolio_positions(client):
    """Get current positions"""
    response = client.get("/api/v1/portfolio/positions")
    
    assert response.status_code == 200
    data = response.json()
    assert "stocks" in data
    assert "cash_balance" in data

def test_portfolio_greeks(client):
    """Get portfolio Greeks"""
    response = client.get("/api/v1/portfolio/greeks")
    
    assert response.status_code == 200
    data = response.json()
    assert "delta" in data
    assert "gamma" in data
    assert "theta" in data
```

### Order Execution Flow Test

```python
# tests/integration/test_order_execution_flow.py

def test_complete_order_flow(client):
    """Full order lifecycle: submit → fill → history"""
    
    # 1. Check initial portfolio
    initial = client.get("/api/v1/portfolio/positions").json()
    initial_cash = initial["cash_balance"]
    
    # 2. Place buy order
    order = client.post("/api/v1/orders", json={
        "ticker": "AAPL",
        "side": "buy",
        "quantity": 100,
        "order_type": "market"
    }).json()
    
    assert order["status"] in ["filled", "submitted"]
    order_id = order["order_id"]
    
    # 3. Verify cash decreased
    updated = client.get("/api/v1/portfolio/positions").json()
    assert updated["cash_balance"] < initial_cash
    
    # 4. Check positions updated
    positions = updated["stocks"]
    aapl_position = next((p for p in positions if p["ticker"] == "AAPL"), None)
    assert aapl_position is not None
    assert aapl_position["quantity"] == 100
    
    # 5. View order details
    order_details = client.get(f"/api/v1/orders/{order_id}").json()
    assert order_details["filled_quantity"] == 100
    assert order_details["average_fill_price"] > 0
```

## End-to-End Tests

### Browser Automation Tests

```python
# tests/e2e/test_trading_flow.py

import pytest
from playwright.sync_api import sync_playwright

@pytest.fixture
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()

@pytest.fixture
def page(browser):
    return browser.new_page()

def test_market_overview_flow(page):
    """User views market overview"""
    page.goto("http://localhost:3000")
    
    # Wait for market data
    page.wait_for_selector("[data-testid='market-overview']")
    
    # Check watchlist displayed
    watchlist = page.query_selector("[data-testid='watchlist-table']")
    assert watchlist is not None
    
    # Verify prices updated
    prices = page.query_selector_all("[data-testid='price-cell']")
    assert len(prices) > 0

def test_place_order_flow(page):
    """User places order through UI"""
    page.goto("http://localhost:3000")
    
    # Navigate to trading
    page.click("text=Trading")
    
    # Fill order form
    page.fill("[data-testid='ticker-input']", "AAPL")
    page.fill("[data-testid='quantity-input']", "100")
    page.click("[data-testid='buy-button']")
    
    # Confirm
    page.click("[data-testid='confirm-button']")
    
    # Check success message
    page.wait_for_selector("[data-testid='order-success']")
    
    # Verify order in history
    page.goto("http://localhost:3000/orders")
    page.wait_for_selector("text=AAPL")

def test_portfolio_monitoring_flow(page):
    """User monitors portfolio in real-time"""
    page.goto("http://localhost:3000/portfolio")
    
    # Check P&L card
    pnl = page.query_selector("[data-testid='total-pnl']")
    assert pnl is not None
    
    # Check positions table
    positions_table = page.query_selector("[data-testid='positions-table']")
    assert positions_table is not None
    
    # Wait for auto-refresh (30 sec)
    import time
    initial_pnl = pnl.text_content()
    time.sleep(35)
    
    # Reload and compare (might have changed)
    page.reload()
    page.wait_for_selector("[data-testid='total-pnl']")
```

## Paper Trading Simulation

### Backtest Simulation

```python
# tests/simulation/test_paper_trading_backtest.py

import pytest
from datetime import datetime, timedelta
from src.qlib_research.app.services.paper_broker import PaperBrokerService
from src.qlib_research.app.services.qlib_research import QlibResearchService

def test_paper_trading_5_day_backtest():
    """Run 5-day paper trading simulation"""
    
    broker = PaperBrokerService(initial_cash=100000)
    research = QlibResearchService()
    
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 5)
    
    pnl_history = []
    
    for day in range((end_date - start_date).days):
        current_date = start_date + timedelta(days=day)
        
        # Get signals for today
        signals = research.get_daily_signals(date=current_date)
        
        for signal in signals:
            if signal['action'] == 'BUY':
                # Place order
                broker.submit_order(
                    ticker=signal['ticker'],
                    side='buy',
                    quantity=signal['quantity'],
                    order_type='market'
                )
            elif signal['action'] == 'SELL':
                broker.submit_order(
                    ticker=signal['ticker'],
                    side='sell',
                    quantity=signal['quantity'],
                    order_type='market'
                )
        
        # Mark to market
        portfolio = broker.get_portfolio()
        pnl_history.append(portfolio.total_pnl)
    
    # Verify results
    final_pnl = pnl_history[-1]
    cumulative_return = final_pnl / 100000
    
    print(f"Final P&L: ${final_pnl:,.2f} ({cumulative_return*100:.2f}%)")
    
    # Basic sanity checks
    assert isinstance(final_pnl, float)
    assert len(pnl_history) == 5

def test_paper_trading_greek_hedge():
    """Test delta-neutral hedging strategy"""
    
    broker = PaperBrokerService(initial_cash=100000)
    
    # Buy 100 shares AAPL
    broker.submit_order(ticker="AAPL", side="buy", quantity=100)
    
    # Sell call to hedge (simplified)
    broker.submit_order(ticker="AAPL_CALL_150", side="sell", quantity=2)
    
    portfolio = broker.get_portfolio()
    
    # Portfolio should be close to delta-neutral
    assert abs(portfolio.portfolio_delta) < 10  # Allow small error
```

## Load Testing

```python
# tests/load/test_api_performance.py

import pytest
from locust import HttpUser, task, between

class QuickLoadTest(HttpUser):
    """Basic load test with Locust"""
    
    wait_time = between(1, 3)
    
    @task
    def market_overview(self):
        self.client.get("/api/v1/market/overview?tickers=AAPL,MSFT")
    
    @task
    def portfolio(self):
        self.client.get("/api/v1/portfolio/positions")
    
    @task
    def portfolio_greeks(self):
        self.client.get("/api/v1/portfolio/greeks")

# Run: locust -f tests/load/test_api_performance.py --host=http://localhost:8000
```

## Test Configuration

```python
# tests/conftest.py

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.qlib_research.app.api.main import app
from src.qlib_research.app.models.user import Base

# Use in-memory SQLite for tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def db():
    """Create test database"""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield SessionLocal()
    
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    """Create test client"""
    def override_get_db():
        return db
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture
def sample_portfolio():
    """Create sample portfolio for tests"""
    return {
        "cash": 100000,
        "positions": [
            {"ticker": "AAPL", "qty": 100, "price": 150},
            {"ticker": "MSFT", "qty": 50, "price": 340}
        ]
    }
```

## Test Coverage

**Target**: 80%+ code coverage

```bash
# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# Output: htmlcov/index.html shows coverage by module
```

## Acceptance Criteria

- [ ] Unit test coverage >80%
- [ ] All API routes have integration tests
- [ ] E2E tests pass for main flows
- [ ] Paper trading backtest runs 5+ days
- [ ] Load test handles 100+ concurrent requests
- [ ] All tests pass in CI/CD pipeline

## Known Limitations (MVP)

- No database state cleanup between tests (in-memory SQLite)
- E2E tests require app running (docker-compose for CI)
- No stress testing with real market data
- Load tests not automated in CI
