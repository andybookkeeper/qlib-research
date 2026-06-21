# tests/unit/test_qlib_service.py
"""Unit tests for Qlib service."""

import pytest
from src.qlib_research.app.services.qlib_service import QlibService


def test_qlib_service_init():
    """Test QlibService initialization."""
    service = QlibService(region="US")
    
    assert service.region == "US"
    assert service.initialized is False


def test_qlib_service_available_tickers():
    """Test getting available tickers."""
    service = QlibService()
    
    tickers = service.get_available_tickers(market="us")
    
    assert len(tickers) > 0
    assert "AAPL" in tickers
    assert "TSLA" in tickers


# Note: Full integration tests require Qlib/Yahoo Finance connectivity
