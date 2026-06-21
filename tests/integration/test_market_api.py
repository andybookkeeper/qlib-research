# tests/integration/test_market_api.py
"""Integration tests for market API endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.qlib_research.app.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestMarketAPI:
    """Test market data API."""
    
    def test_get_available_tickers(self, client):
        """Test getting available tickers."""
        
        response = client.get("/api/market/tickers")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "AAPL" in data
    
    def test_get_cache_status(self, client):
        """Test cache status endpoint."""
        
        response = client.get("/api/market/cache/status")
        
        assert response.status_code == 200
        data = response.json()
        assert 'total' in data
        assert 'fresh' in data
        assert 'stale' in data
        assert 'coverage_pct' in data
    
    def test_get_refresh_suggestion(self, client):
        """Test refresh suggestion endpoint."""
        
        response = client.get("/api/market/cache/refresh-suggestion")
        
        assert response.status_code == 200
        data = response.json()
        assert 'refresh_urgent' in data
        assert 'refresh_soon' in data
        assert 'message' in data
    
    def test_get_missing_data(self, client):
        """Test missing data endpoint."""
        
        response = client.get("/api/market/cache/missing")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Initially many will be missing
        assert len(data) >= 0
    
    # Note: Price endpoints require actual market data
    # These are integration tests that need live data
