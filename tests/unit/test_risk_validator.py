# tests/unit/test_risk_validator.py
"""Unit tests for risk validator."""

import pytest
from datetime import datetime, timedelta
import numpy as np

from src.qlib_research.app.services.risk_validator import (
    RiskValidator,
    RiskLimits,
    GreeksAggregation,
    RiskViolation
)


class TestRiskValidator:
    """Test risk validator."""
    
    def test_initialization(self):
        """Test validator initialization."""
        validator = RiskValidator()
        
        assert validator.limits is not None
        assert validator.limits.max_position_size == 50000.0
        assert validator.limits.max_concentration == 0.25
    
    def test_custom_limits(self):
        """Test custom limits."""
        limits = RiskLimits(
            max_position_size=100000.0,
            max_concentration=0.5
        )
        validator = RiskValidator(limits)
        
        assert validator.limits.max_position_size == 100000.0
        assert validator.limits.max_concentration == 0.5


class TestPositionValidation:
    """Test position size validation."""
    
    def test_position_within_limits(self):
        """Test valid position size."""
        validator = RiskValidator()
        
        violation = validator.validate_position_size(
            position_value=10000.0,
            portfolio_value=100000.0,
            position_name="AAPL"
        )
        
        assert violation is None
    
    def test_position_exceeds_size_limit(self):
        """Test position exceeds absolute size limit."""
        validator = RiskValidator()
        
        violation = validator.validate_position_size(
            position_value=100000.0,  # Exceeds 50000 limit
            portfolio_value=500000.0,
            position_name="AAPL"
        )
        
        assert violation is not None
        assert violation.limit_name == "max_position_size"
        assert violation.severity == "error"
    
    def test_position_exceeds_concentration_limit(self):
        """Test position exceeds concentration limit."""
        validator = RiskValidator()
        
        violation = validator.validate_position_size(
            position_value=30000.0,  # 30% of 100k portfolio
            portfolio_value=100000.0,
            position_name="AAPL"
        )
        
        assert violation is not None
        assert violation.limit_name == "max_concentration"
        assert violation.severity == "warning"


class TestGreeksAggregation:
    """Test Greeks aggregation."""
    
    def test_aggregate_stock_positions(self):
        """Test aggregating stock Greeks."""
        validator = RiskValidator()
        
        positions = {
            "AAPL": {
                "quantity": 100,
                "is_option": False
            },
            "MSFT": {
                "quantity": -50,
                "is_option": False
            }
        }
        
        greeks = validator.aggregate_greeks(positions)
        
        assert greeks.delta == 50  # 100 - 50
        assert greeks.gamma == 0
        assert greeks.theta == 0
    
    def test_aggregate_option_positions(self):
        """Test aggregating option Greeks."""
        validator = RiskValidator()
        
        positions = {
            "CALL_AAPL": {
                "quantity": 1,
                "is_option": True,
                "delta": 0.5,
                "gamma": 0.02,
                "theta": -0.05,
                "vega": 0.3,
                "rho": 0.1
            }
        }
        
        greeks = validator.aggregate_greeks(positions)
        
        assert greeks.delta == 0.5
        assert greeks.gamma == 0.02
        assert greeks.theta == -0.05
        assert greeks.vega == 0.3
        assert greeks.rho == 0.1
    
    def test_aggregate_mixed_positions(self):
        """Test aggregating mixed stock and option positions."""
        validator = RiskValidator()
        
        positions = {
            "AAPL": {
                "quantity": 100,
                "is_option": False
            },
            "CALL_AAPL": {
                "quantity": 2,
                "is_option": True,
                "delta": 0.6,
                "gamma": 0.03,
                "theta": -0.10,
                "vega": 0.5,
                "rho": 0.2
            }
        }
        
        greeks = validator.aggregate_greeks(positions)
        
        assert greeks.delta == 101.2  # 100 + 2*0.6
        assert greeks.gamma == 0.06  # 2*0.03
        assert greeks.theta == -0.20  # 2*-0.10


class TestVaRCalculation:
    """Test Value at Risk calculation."""
    
    def test_var_with_returns(self):
        """Test VaR calculation with returns."""
        validator = RiskValidator()
        
        # Simulate returns: mostly small, one large loss
        returns = [-0.02, 0.01, -0.01, 0.02, -0.15, 0.01]
        
        var = validator.calculate_var(
            portfolio_value=100000.0,
            returns=returns,
            confidence=0.95
        )
        
        assert var > 0
        assert var < 100000  # Sanity check
    
    def test_var_empty_returns(self):
        """Test VaR with empty returns."""
        validator = RiskValidator()
        
        var = validator.calculate_var(
            portfolio_value=100000.0,
            returns=[],
            confidence=0.95
        )
        
        assert var == 0.0


class TestMaxDrawdown:
    """Test maximum drawdown calculation."""
    
    def test_max_drawdown_with_declining_values(self):
        """Test max drawdown with declining portfolio."""
        validator = RiskValidator()
        
        # Portfolio: 100 -> 120 (peak) -> 100 -> 80 (trough)
        values = [100, 110, 120, 100, 80]
        
        max_dd = validator.calculate_max_drawdown(values)
        
        # Drawdown from 120 to 80 = -33.33%
        assert max_dd < -0.33
        assert max_dd > -0.34
    
    def test_max_drawdown_always_increasing(self):
        """Test max drawdown with always increasing values."""
        validator = RiskValidator()
        
        values = [100, 110, 120, 130, 140]
        
        max_dd = validator.calculate_max_drawdown(values)
        
        # No drawdown
        assert max_dd == 0.0
    
    def test_max_drawdown_single_value(self):
        """Test max drawdown with single value."""
        validator = RiskValidator()
        
        max_dd = validator.calculate_max_drawdown([100])
        
        assert max_dd == 0.0


class TestSharpeRatio:
    """Test Sharpe ratio calculation."""
    
    def test_sharpe_ratio_positive_returns(self):
        """Test Sharpe ratio with positive returns."""
        validator = RiskValidator()
        
        # Consistent small positive returns with slight variation
        np.random.seed(42)
        returns = (np.ones(252) * 0.001 + np.random.normal(0, 0.001, 252)).tolist()
        
        sharpe = validator.calculate_sharpe_ratio(
            returns=returns,
            risk_free_rate=0.02
        )
        
        # Should be a reasonable number with these returns
        assert isinstance(sharpe, float)
        assert not np.isinf(sharpe)
    
    def test_sharpe_ratio_volatile_returns(self):
        """Test Sharpe ratio with volatile returns."""
        validator = RiskValidator()
        
        # High volatility, neutral mean
        np.random.seed(42)
        returns = np.random.normal(0, 0.05, 252).tolist()
        
        sharpe = validator.calculate_sharpe_ratio(returns)
        
        assert isinstance(sharpe, float)
    
    def test_sharpe_ratio_empty_returns(self):
        """Test Sharpe ratio with empty returns."""
        validator = RiskValidator()
        
        sharpe = validator.calculate_sharpe_ratio([])
        
        assert sharpe == 0.0


class TestGreeksValidation:
    """Test Greeks limit validation."""
    
    def test_delta_within_limits(self):
        """Test delta within limits."""
        validator = RiskValidator()
        
        greeks = GreeksAggregation(delta=1.5)
        
        violations = validator.validate_greeks(greeks)
        
        # No violations
        delta_violations = [v for v in violations if v.limit_name == "max_portfolio_delta"]
        assert len(delta_violations) == 0
    
    def test_delta_exceeds_limits(self):
        """Test delta exceeds limits."""
        validator = RiskValidator()
        
        greeks = GreeksAggregation(delta=5.0)  # Exceeds 2.0 limit
        
        violations = validator.validate_greeks(greeks)
        
        delta_violations = [v for v in violations if v.limit_name == "max_portfolio_delta"]
        assert len(delta_violations) > 0
        assert delta_violations[0].severity == "warning"
    
    def test_vega_exceeds_limits(self):
        """Test vega exceeds limits."""
        validator = RiskValidator()
        
        greeks = GreeksAggregation(vega=2000.0)  # Exceeds 1000 limit
        
        violations = validator.validate_greeks(greeks)
        
        vega_violations = [v for v in violations if v.limit_name == "max_portfolio_vega"]
        assert len(vega_violations) > 0


class TestDrawdownValidation:
    """Test drawdown limit validation."""
    
    def test_drawdown_within_limits(self):
        """Test drawdown within limits."""
        validator = RiskValidator()
        
        violation = validator.validate_drawdown(-0.15)  # 15% drawdown
        
        assert violation is None
    
    def test_drawdown_exceeds_limits(self):
        """Test drawdown exceeds 20% limit."""
        validator = RiskValidator()
        
        violation = validator.validate_drawdown(-0.25)  # 25% drawdown
        
        assert violation is not None
        assert violation.limit_name == "max_drawdown"
        assert violation.severity == "error"


class TestSharpeValidation:
    """Test Sharpe ratio limit validation."""
    
    def test_sharpe_above_minimum(self):
        """Test Sharpe ratio above minimum."""
        validator = RiskValidator()
        
        violation = validator.validate_sharpe_ratio(1.0)
        
        assert violation is None
    
    def test_sharpe_below_minimum(self):
        """Test Sharpe ratio below minimum 0.5."""
        validator = RiskValidator()
        
        violation = validator.validate_sharpe_ratio(0.3)
        
        assert violation is not None
        assert violation.limit_name == "min_sharpe_ratio"
        assert violation.severity == "warning"


class TestPortfolioValidation:
    """Test comprehensive portfolio validation."""
    
    def test_validate_compliant_portfolio(self):
        """Test validating compliant portfolio."""
        validator = RiskValidator()
        
        positions = {
            "AAPL": {
                "market_value": 10000,
                "cost_basis": 9500,
                "quantity": 100,
                "is_option": False
            }
        }
        
        risk, violations = validator.validate_portfolio(
            portfolio_value=100000,
            cash=90000,
            positions=positions,
            portfolio_values=[100000],
            pnl_returns=[0.001],
            realized_pnl=0
        )
        
        assert risk.total_value == 100000
        assert risk.leverage < 1.1
        assert len([v for v in violations if v.severity == "error"]) == 0
    
    def test_validate_noncompliant_portfolio(self):
        """Test validating non-compliant portfolio."""
        validator = RiskValidator()
        
        positions = {
            "AAPL": {
                "market_value": 100000,  # Exceeds size limit
                "cost_basis": 95000,
                "quantity": 1000,
                "is_option": False
            }
        }
        
        risk, violations = validator.validate_portfolio(
            portfolio_value=100000,
            cash=0,
            positions=positions,
            portfolio_values=[100000],
            pnl_returns=[0.001],
            realized_pnl=0
        )
        
        assert len(violations) > 0
        # Should have position size violation
        size_violations = [v for v in violations if v.limit_name == "max_position_size"]
        assert len(size_violations) > 0
