# Implement Full API Integration Specification
# Connect all backend services to unified FastAPI server

## Complete API Routes

```python
# src/qlib_research/app/api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.qlib_research.app.api.routes import (
    market,
    trading,
    portfolio,
    research,
    monitoring,
    signals
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown events"""
    
    # Startup
    logger.info("Starting FastAPI app...")
    await market_service.initialize()
    await signal_bridge.bridge.qlib.initialize()
    scheduler.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    scheduler.stop()
    await market_service.close()

app = FastAPI(
    title="Qlib Trading App",
    description="Quantitative trading with Qlib",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(market.router, prefix="/api/market", tags=["market"])
app.include_router(trading.router, prefix="/api/trading", tags=["trading"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(research.router, prefix="/api/research", tags=["research"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["monitoring"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])

@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    """API root"""
    return {
        "app": "Qlib Trading Platform",
        "version": "0.1.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )
```

## Complete Test Suite

```python
# tests/test_api_integration.py

@pytest.mark.asyncio
async def test_api_endpoints_all_connected():
    """Verify all endpoints reachable"""
    
    client = TestClient(app)
    
    endpoints = [
        ("GET", "/api/market/ohlcv/AAPL"),
        ("GET", "/api/trading/portfolio"),
        ("GET", "/api/portfolio/positions"),
        ("GET", "/api/research/models"),
        ("GET", "/api/monitoring/health"),
        ("GET", "/api/signals/today"),
    ]
    
    for method, path in endpoints:
        response = client.request(method, path)
        assert response.status_code in [200, 400]  # 400 ok for missing query params

@pytest.mark.asyncio
async def test_order_flow_end_to_end():
    """Complete order lifecycle"""
    
    client = TestClient(app)
    
    # 1. Submit order
    response = client.post("/api/trading/orders", json={
        "ticker": "AAPL",
        "side": "buy",
        "quantity": 100
    })
    assert response.status_code == 200
    order = response.json()
    order_id = order['id']
    
    # 2. Get portfolio
    response = client.get("/api/trading/portfolio")
    assert response.status_code == 200
    
    # 3. Cancel order
    response = client.delete(f"/api/trading/orders/{order_id}")
    assert response.status_code == 200
```

## Acceptance Criteria

- [ ] All routes integrated
- [ ] CORS configured
- [ ] Health check working
- [ ] Error handling middleware
- [ ] Request/response logging
- [ ] All tests passing
- [ ] API documentation on /docs
- [ ] Database connections pooled
