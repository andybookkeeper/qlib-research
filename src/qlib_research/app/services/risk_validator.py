# src/qlib_research/app/services/risk_validator.py
"""Risk validation and portfolio metrics engine."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class RiskLimits:
    """Risk limit thresholds."""
    max_position_size: float = 50000.0  # Max $ per position
    max_concentration: float = 0.25  # Max % of portfolio in one position
    max_portfolio_delta: float = 2.0  # Max net delta exposure
    max_portfolio_gamma: float = 0.5  # Max gamma exposure
    max_portfolio_theta: float = -500.0  # Min theta (time decay)
    max_portfolio_vega: float = 1000.0  # Max vega exposure
    max_drawdown: float = 0.20  # Max 20% drawdown
    min_sharpe_ratio: float = 0.5  # Minimum Sharpe ratio


@dataclass
class GreeksAggregation:
    """Portfolio-level Greeks."""
    delta: float = 0.0  # Directional exposure
    gamma: float = 0.0  # Convexity exposure
    theta: float = 0.0  # Time decay per day
    vega: float = 0.0   # Volatility exposure per 1% vol move
    rho: float = 0.0    # Interest rate exposure


@dataclass
class PortfolioRisk:
    """Portfolio risk metrics."""
    total_value: float
    cash: float
    gross_value: float  # All long positions
    net_value: float    # Long - short
    
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    total_pnl_pct: float
    
    var_95: float  # Value at Risk (95% confidence)
    max_drawdown: float  # Historical max drawdown
    sharpe_ratio: float  # Risk-adjusted returns
    
    greeks: GreeksAggregation
    leverage: float  # Gross value / total value
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'total_value': self.total_value,
            'cash': self.cash,
            'gross_value': self.gross_value,
            'net_value': self.net_value,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl,
            'total_pnl': self.total_pnl,
            'total_pnl_pct': self.total_pnl_pct,
            'var_95': self.var_95,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'greeks': {
                'delta': self.greeks.delta,
                'gamma': self.greeks.gamma,
                'theta': self.greeks.theta,
                'vega': self.greeks.vega,
                'rho': self.greeks.rho
            },
            'leverage': self.leverage
        }


@dataclass
class RiskViolation:
    """Single risk limit violation."""
    limit_name: str
    current_value: float
    limit_value: float
    severity: str  # 'warning', 'error'
    message: str


class RiskValidator:
    """Validates portfolio risk and position limits."""
    
    def __init__(self, limits: Optional[RiskLimits] = None):
        """
        Initialize risk validator.
        
        Args:
            limits: Risk limit configuration (defaults to RiskLimits())
        """
        self.limits = limits or RiskLimits()
        self.pnl_history: List[float] = []  # For Sharpe calculation
    
    def validate_position_size(
        self,
        position_value: float,
        portfolio_value: float,
        position_name: str = "Position"
    ) -> Optional[RiskViolation]:
        """
        Check if position size exceeds limits.
        
        Args:
            position_value: Market value of position
            portfolio_value: Total portfolio value
            position_name: Name of position for error message
        
        Returns:
            RiskViolation if limit exceeded, None otherwise
        """
        # Check absolute size
        if abs(position_value) > self.limits.max_position_size:
            return RiskViolation(
                limit_name="max_position_size",
                current_value=abs(position_value),
                limit_value=self.limits.max_position_size,
                severity="error",
                message=f"{position_name}: position ${abs(position_value):,.0f} exceeds max ${self.limits.max_position_size:,.0f}"
            )
        
        # Check concentration
        if portfolio_value > 0:
            concentration = abs(position_value) / portfolio_value
            if concentration > self.limits.max_concentration:
                return RiskViolation(
                    limit_name="max_concentration",
                    current_value=concentration * 100,
                    limit_value=self.limits.max_concentration * 100,
                    severity="warning",
                    message=f"{position_name}: {concentration*100:.1f}% concentration exceeds {self.limits.max_concentration*100:.1f}%"
                )
        
        return None
    
    def validate_greeks(
        self,
        greeks: GreeksAggregation
    ) -> List[RiskViolation]:
        """
        Check if portfolio Greeks exceed limits.
        
        Args:
            greeks: Portfolio Greeks aggregation
        
        Returns:
            List of violations
        """
        violations = []
        
        # Delta limit
        if abs(greeks.delta) > self.limits.max_portfolio_delta:
            violations.append(RiskViolation(
                limit_name="max_portfolio_delta",
                current_value=greeks.delta,
                limit_value=self.limits.max_portfolio_delta,
                severity="warning",
                message=f"Portfolio delta {greeks.delta:.2f} exceeds limit {self.limits.max_portfolio_delta:.2f}"
            ))
        
        # Gamma limit
        if abs(greeks.gamma) > self.limits.max_portfolio_gamma:
            violations.append(RiskViolation(
                limit_name="max_portfolio_gamma",
                current_value=greeks.gamma,
                limit_value=self.limits.max_portfolio_gamma,
                severity="warning",
                message=f"Portfolio gamma {greeks.gamma:.4f} exceeds limit {self.limits.max_portfolio_gamma:.4f}"
            ))
        
        # Theta limit (minimum time decay)
        if greeks.theta < self.limits.max_portfolio_theta:
            violations.append(RiskViolation(
                limit_name="max_portfolio_theta",
                current_value=greeks.theta,
                limit_value=self.limits.max_portfolio_theta,
                severity="warning",
                message=f"Portfolio theta {greeks.theta:.2f} below limit {self.limits.max_portfolio_theta:.2f}"
            ))
        
        # Vega limit
        if abs(greeks.vega) > self.limits.max_portfolio_vega:
            violations.append(RiskViolation(
                limit_name="max_portfolio_vega",
                current_value=greeks.vega,
                limit_value=self.limits.max_portfolio_vega,
                severity="warning",
                message=f"Portfolio vega {greeks.vega:.2f} exceeds limit {self.limits.max_portfolio_vega:.2f}"
            ))
        
        return violations
    
    def calculate_var(
        self,
        portfolio_value: float,
        returns: List[float],
        confidence: float = 0.95
    ) -> float:
        """
        Calculate Value at Risk (VaR).
        
        Args:
            portfolio_value: Current portfolio value
            returns: Historical returns for volatility
            confidence: Confidence level (0.95 = 95%)
        
        Returns:
            Maximum loss at confidence level
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        # Use percentile method (historical VaR)
        returns_array = np.array(returns)
        var_percentile = np.percentile(returns_array, (1 - confidence) * 100)
        
        # Convert to dollar amount
        var_dollars = portfolio_value * abs(var_percentile)
        
        return var_dollars
    
    def calculate_max_drawdown(
        self,
        portfolio_values: List[float]
    ) -> float:
        """
        Calculate maximum historical drawdown.
        
        Args:
            portfolio_values: Time series of portfolio values
        
        Returns:
            Maximum drawdown as percentage
        """
        if not portfolio_values or len(portfolio_values) < 2:
            return 0.0
        
        values = np.array(portfolio_values)
        
        # Running maximum
        running_max = np.maximum.accumulate(values)
        
        # Drawdown
        drawdown = (values - running_max) / running_max
        
        # Max drawdown
        max_dd = np.min(drawdown)
        
        return max_dd
    
    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.02
    ) -> float:
        """
        Calculate Sharpe ratio.
        
        Args:
            returns: List of period returns (daily, weekly, etc)
            risk_free_rate: Annual risk-free rate
        
        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        
        # Average return
        avg_return = np.mean(returns_array)
        
        # Volatility
        volatility = np.std(returns_array)
        
        if volatility == 0:
            return 0.0
        
        # Annualization factor (assuming daily returns)
        periods_per_year = 252
        annual_excess_return = avg_return * periods_per_year
        annual_volatility = volatility * np.sqrt(periods_per_year)
        
        sharpe = (annual_excess_return - risk_free_rate) / annual_volatility
        
        return sharpe
    
    def aggregate_greeks(
        self,
        positions: Dict[str, Dict]
    ) -> GreeksAggregation:
        """
        Aggregate Greeks across all positions.
        
        Args:
            positions: Dict of {ticker: {delta, gamma, theta, vega, rho, quantity}}
        
        Returns:
            Aggregated Greeks
        """
        greeks = GreeksAggregation()
        
        for ticker, pos_data in positions.items():
            quantity = pos_data.get('quantity', 0)
            
            # Stocks: delta = 1, others = 0
            # Options: use provided Greeks
            if pos_data.get('is_option', False):
                greeks.delta += pos_data.get('delta', 0) * quantity
                greeks.gamma += pos_data.get('gamma', 0) * quantity
                greeks.theta += pos_data.get('theta', 0) * quantity
                greeks.vega += pos_data.get('vega', 0) * quantity
                greeks.rho += pos_data.get('rho', 0) * quantity
            else:
                # Stock position
                greeks.delta += 1.0 * quantity
        
        return greeks
    
    def validate_drawdown(
        self,
        current_drawdown: float
    ) -> Optional[RiskViolation]:
        """
        Check if current drawdown exceeds limit.
        
        Args:
            current_drawdown: Current drawdown as decimal (-0.20 for -20%)
        
        Returns:
            RiskViolation if limit exceeded, None otherwise
        """
        if current_drawdown < -self.limits.max_drawdown:
            return RiskViolation(
                limit_name="max_drawdown",
                current_value=current_drawdown * 100,
                limit_value=-self.limits.max_drawdown * 100,
                severity="error",
                message=f"Portfolio drawdown {current_drawdown*100:.1f}% exceeds maximum {-self.limits.max_drawdown*100:.1f}%"
            )
        
        return None
    
    def validate_sharpe_ratio(
        self,
        sharpe: float
    ) -> Optional[RiskViolation]:
        """
        Check if Sharpe ratio meets minimum threshold.
        
        Args:
            sharpe: Current Sharpe ratio
        
        Returns:
            RiskViolation if below limit, None otherwise
        """
        if sharpe < self.limits.min_sharpe_ratio:
            return RiskViolation(
                limit_name="min_sharpe_ratio",
                current_value=sharpe,
                limit_value=self.limits.min_sharpe_ratio,
                severity="warning",
                message=f"Sharpe ratio {sharpe:.2f} below minimum {self.limits.min_sharpe_ratio:.2f}"
            )
        
        return None
    
    def validate_portfolio(
        self,
        portfolio_value: float,
        cash: float,
        positions: Dict[str, Dict],
        portfolio_values: List[float],
        pnl_returns: List[float],
        realized_pnl: float = 0.0
    ) -> Tuple[PortfolioRisk, List[RiskViolation]]:
        """
        Comprehensive portfolio risk validation.
        
        Args:
            portfolio_value: Total portfolio value
            cash: Available cash
            positions: {ticker: {market_value, quantity, ...}}
            portfolio_values: Historical portfolio values
            pnl_returns: Historical returns
            realized_pnl: Realized P&L to date
        
        Returns:
            (PortfolioRisk metrics, List of violations)
        """
        violations = []
        
        # Calculate gross and net values
        gross_value = sum(abs(p.get('market_value', 0)) for p in positions.values())
        net_value = sum(p.get('market_value', 0) for p in positions.values())
        
        # Calculate metrics
        unrealized_pnl = net_value - sum(p.get('cost_basis', 0) for p in positions.values())
        total_pnl = realized_pnl + unrealized_pnl
        total_pnl_pct = total_pnl / portfolio_value if portfolio_value > 0 else 0
        
        # Risk metrics
        var = self.calculate_var(portfolio_value, pnl_returns)
        max_dd = self.calculate_max_drawdown(portfolio_values)
        sharpe = self.calculate_sharpe_ratio(pnl_returns)
        greeks = self.aggregate_greeks(positions)
        leverage = gross_value / portfolio_value if portfolio_value > 0 else 0
        
        # Create risk report
        risk = PortfolioRisk(
            total_value=portfolio_value,
            cash=cash,
            gross_value=gross_value,
            net_value=net_value,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            var_95=var,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            greeks=greeks,
            leverage=leverage
        )
        
        # Run validations
        
        # Check individual positions
        for ticker, pos_data in positions.items():
            violation = self.validate_position_size(
                pos_data.get('market_value', 0),
                portfolio_value,
                ticker
            )
            if violation:
                violations.append(violation)
        
        # Check Greeks
        violations.extend(self.validate_greeks(greeks))
        
        # Check drawdown
        dd_violation = self.validate_drawdown(max_dd)
        if dd_violation:
            violations.append(dd_violation)
        
        # Check Sharpe
        sharpe_violation = self.validate_sharpe_ratio(sharpe)
        if sharpe_violation:
            violations.append(sharpe_violation)
        
        return risk, violations
