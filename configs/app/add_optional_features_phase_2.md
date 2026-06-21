# Add Optional Features (Phase 2) Specification
# Enhancements beyond MVP

## Live Broker Integration (Optional)

```python
# src/qlib_research/app/brokers/live_broker.py

class IBKRBroker:
    """Interactive Brokers live trading"""
    
    def __init__(self, account_id: str, paper_trading: bool = True):
        self.account_id = account_id
        self.paper_trading = paper_trading
        self.ib = IB()
    
    async def connect(self):
        """Connect to IBKR"""
        await self.ib.connectAsync('127.0.0.1', 7497, clientId=1)
    
    async def submit_live_order(self, order_request):
        """Submit live order (if enabled)"""
        
        if not self.paper_trading:
            # Real trading
            return await self._submit_real_order(order_request)
        else:
            # Paper trading
            return await self._submit_paper_order(order_request)
```

## Intraday Trading (Optional)

```python
# src/qlib_research/app/features/intraday.py

class IntradayPipeline:
    """Intraday 1-minute data"""
    
    def __init__(self):
        self.cache = {}
    
    async def get_minute_bars(self, ticker: str, count: int = 100):
        """Fetch last N minute bars"""
        
        # Use yfinance or broker API
        data = yf.download(
            ticker,
            period='1d',
            interval='1m'
        )
        
        return data.tail(count)
```

## Options Trading Integration (Optional)

```python
# src/qlib_research/app/features/options_trading.py

class OptionsTradingEngine:
    """Options order entry and Greeks aggregation"""
    
    def place_option_order(
        self,
        underlying: str,
        strike: float,
        expiry: str,
        option_type: str,  # "CALL" or "PUT"
        side: str,
        quantity: int
    ):
        """Place options order (read-only in MVP)"""
        
        # MVP: Disabled pending data validation
        raise NotImplementedError(
            "Options trading deferred to Phase 2. "
            "Yahoo Finance IV data unreliable for live trading."
        )
```

## Machine Learning Enhancements (Optional)

```python
# Optional in Phase 2:
# - XGBoost, CatBoost models
# - Neural networks (LSTM)
# - Ensemble methods
# - Model stacking
# - Hyperparameter optimization (Optuna)
# - Automated feature engineering (featuretools)
```

## Deployment Enhancements (Optional)

```yaml
# Optional Phase 2 deployment targets:
# - AWS (ECS, Lambda)
# - GCP (Cloud Run, App Engine)
# - Azure (Container Instances)
# - Kubernetes (production scale)
# - CI/CD (GitHub Actions, GitLab CI)
```

## Acceptance Criteria (Phase 2)

- [ ] Live broker SDK integrated
- [ ] Intraday data pipeline
- [ ] Options trading enabled
- [ ] Advanced ML models
- [ ] Production deployment setup
