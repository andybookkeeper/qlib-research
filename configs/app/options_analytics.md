# Options Analytics Specification
# Options chain display, Greeks calculation, and risk analysis (Read-Only in MVP)

## Overview

The options analytics module provides:
1. **Options Chain Display**: Calls and puts organized by expiration and strike
2. **Greeks Calculation**: Delta, gamma, theta, vega, rho for pricing and risk
3. **Implied Volatility**: Estimated IV from market prices
4. **Risk Analysis**: Position Greeks aggregation
5. **Data Provider**: External API (not Qlib-native)

**MVP Scope**: Read-only display. Order entry disabled until external data source is integrated and tested.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              External Options Data Provider                  │
│  - Alpha Vantage (free tier)                                 │
│  - OptionChain API (if available)                            │
│  - Broker API (Interactive Brokers, Alpaca, etc.)           │
│  - Yahoo Finance (limited, via yfinance)                    │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│              Options Data Service                            │
│  - Fetch and cache options chain                            │
│  - Validate data quality                                     │
│  - Normalize across providers                               │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│              Greeks Calculator                               │
│  - Black-Scholes pricing model                              │
│  - IV solver (Newton-Raphson)                               │
│  - Greeks computation (delta, gamma, theta, vega, rho)     │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│              API Endpoints                                   │
│  - GET /api/options/chain/{ticker}                          │
│  - GET /api/options/greeks/{ticker}                         │
│  - GET /api/options/implied-vol/{ticker}                    │
│  - GET /api/options/expirations/{ticker}                    │
└──────────────────────────────────────────────────────────────┘
```

## Options Chain Model

### Data Structure

```python
# src/qlib_research/app/models/option.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class OptionContract:
    """Represents a single options contract (call or put)"""
    
    # Identity
    ticker: str                 # Underlying stock (e.g., "AAPL")
    contract_symbol: str       # Full option symbol (e.g., "AAPL 2024-01-19 C150.00")
    
    # Contract details
    contract_type: str         # "call" or "put"
    expiration_date: datetime  # Expiration date (usually 4 PM ET)
    strike_price: float        # Strike price (e.g., 150.00)
    
    # Market data
    current_price: float       # Current bid-ask midpoint
    bid: float                 # Bid price
    ask: float                 # Ask price
    last_price: float          # Last trade price
    volume: int                # Daily volume
    open_interest: int         # Open interest
    
    # Greeks
    delta: float               # Δ (directional risk per $1 move in underlying)
    gamma: float               # Γ (delta acceleration)
    theta: float               # Θ (time decay per day)
    vega: float                # ν (sensitivity to 1% IV change)
    rho: float                 # ρ (sensitivity to interest rate change)
    
    # Implied volatility
    implied_vol: float         # IV as decimal (e.g., 0.25 = 25%)
    
    # Metadata
    last_updated: datetime     # When this data was fetched
    
    @property
    def days_to_expiration(self) -> float:
        """Calculate days until expiration"""
        return (self.expiration_date - datetime.now()).days + 1
    
    @property
    def is_itm(self) -> bool:
        """Is option in-the-money?"""
        underlying_price = self.current_price  # Placeholder; fetch from market data
        if self.contract_type == "call":
            return underlying_price > self.strike_price
        else:  # put
            return underlying_price < self.strike_price
    
    @property
    def intrinsic_value(self) -> float:
        """Intrinsic value (ITM amount)"""
        underlying_price = self.current_price
        if self.contract_type == "call":
            return max(underlying_price - self.strike_price, 0)
        else:
            return max(self.strike_price - underlying_price, 0)
    
    @property
    def time_value(self) -> float:
        """Extrinsic (time) value"""
        return max(self.current_price - self.intrinsic_value, 0)

@dataclass
class OptionsChain:
    """Collection of options contracts for a given expiration"""
    
    ticker: str
    expiration_date: datetime
    underlying_price: float
    
    calls: list[OptionContract]
    puts: list[OptionContract]
    
    @property
    def atm_strike(self) -> float:
        """Find at-the-money strike"""
        all_strikes = [c.strike_price for c in self.calls] + [p.strike_price for p in self.puts]
        return min(all_strikes, key=lambda x: abs(x - self.underlying_price))
```

## Greeks Calculation

### Black-Scholes Formula Implementation

```python
# src/qlib_research/app/services/greeks_calculator.py

import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
from datetime import datetime
from typing import Tuple

class GreeksCalculator:
    """Compute option Greeks using Black-Scholes model"""
    
    @staticmethod
    def black_scholes_price(
        S: float,      # Current stock price
        K: float,      # Strike price
        T: float,      # Time to expiration (years, e.g., 0.25 = 3 months)
        r: float,      # Risk-free rate (e.g., 0.05 = 5%)
        sigma: float,  # Volatility (std dev of returns, e.g., 0.2 = 20%)
        option_type: str = "call"  # "call" or "put"
    ) -> float:
        """
        Black-Scholes option pricing formula.
        
        Returns:
            Theoretical option price
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == "call":
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:  # put
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        
        return price
    
    @staticmethod
    def delta(
        S: float, K: float, T: float, r: float, sigma: float, 
        option_type: str = "call"
    ) -> float:
        """
        Delta: Change in option price per $1 move in underlying.
        
        Range: -1 to 1 (calls: 0-1, puts: -1-0)
        Interpretation: Probability of expiring ITM (approximately)
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        
        if option_type == "call":
            return norm.cdf(d1)
        else:
            return norm.cdf(d1) - 1
    
    @staticmethod
    def gamma(
        S: float, K: float, T: float, r: float, sigma: float
    ) -> float:
        """
        Gamma: Rate of change of delta per $1 move.
        
        Interpretation: How much delta changes as stock price moves
        High gamma = delta more sensitive to price moves
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        return norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    @staticmethod
    def theta(
        S: float, K: float, T: float, r: float, sigma: float,
        option_type: str = "call"
    ) -> float:
        """
        Theta: Time decay per day (negative = value decreases with time).
        
        Interpretation: How much option loses value each day
        Theta accelerates as expiration approaches
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == "call":
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - 
                    r * K * np.exp(-r * T) * norm.cdf(d2))
        else:
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) + 
                    r * K * np.exp(-r * T) * norm.cdf(-d2))
        
        # Convert to per-day (divide by 365)
        return theta / 365
    
    @staticmethod
    def vega(
        S: float, K: float, T: float, r: float, sigma: float
    ) -> float:
        """
        Vega: Change in option price per 1% change in implied volatility.
        
        Interpretation: IV sensitivity. High vega = expensive if IV spikes
        Both calls and puts have positive vega
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        return S * norm.pdf(d1) * np.sqrt(T) / 100  # Per 1% IV change
    
    @staticmethod
    def rho(
        S: float, K: float, T: float, r: float, sigma: float,
        option_type: str = "call"
    ) -> float:
        """
        Rho: Change in option price per 1% change in interest rates.
        
        Interpretation: Interest rate sensitivity (usually small for short-term options)
        """
        d2 = (np.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        
        if option_type == "call":
            return K * T * np.exp(-r * T) * norm.cdf(d2) / 100
        else:
            return -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
    
    @staticmethod
    def compute_all_greeks(
        S: float, K: float, T: float, r: float, sigma: float,
        option_type: str = "call"
    ) -> dict:
        """Compute all Greeks in one call"""
        return {
            "delta": GreeksCalculator.delta(S, K, T, r, sigma, option_type),
            "gamma": GreeksCalculator.gamma(S, K, T, r, sigma),
            "theta": GreeksCalculator.theta(S, K, T, r, sigma, option_type),
            "vega": GreeksCalculator.vega(S, K, T, r, sigma),
            "rho": GreeksCalculator.rho(S, K, T, r, sigma, option_type),
        }
```

### Implied Volatility Solver

```python
class ImpliedVolatilityCalculator:
    """Compute implied volatility from market price (inverse problem)"""
    
    @staticmethod
    def implied_vol(
        market_price: float,  # Observed market price
        S: float,
        K: float,
        T: float,
        r: float,
        option_type: str = "call",
        initial_guess: float = 0.3
    ) -> float:
        """
        Solve for implied volatility using Newton-Raphson.
        
        Find sigma such that BS_price(sigma) = market_price
        """
        
        def objective(sigma):
            bs_price = GreeksCalculator.black_scholes_price(S, K, T, r, sigma, option_type)
            return bs_price - market_price
        
        def derivative(sigma):
            # Use vega as derivative (since d(price)/d(sigma) = vega)
            return GreeksCalculator.vega(S, K, T, r, sigma)
        
        try:
            # Use Brent's method for robustness (handles edge cases)
            iv = brentq(objective, 1e-6, 5.0)  # Search between 0.01% and 500% IV
            return iv
        except ValueError:
            # If no root found, return None or estimate
            return None
```

## Options Data Service

### External Data Provider

```python
# src/qlib_research/app/services/options_data_service.py

from abc import ABC, abstractmethod
import requests
import pandas as pd
from typing import List, Dict

class OptionsDataProvider(ABC):
    """Abstract base for options data providers"""
    
    @abstractmethod
    def fetch_chain(self, ticker: str, expiration: str) -> List[OptionContract]:
        """Fetch options chain for expiration"""
        pass
    
    @abstractmethod
    def fetch_all_expirations(self, ticker: str) -> List[str]:
        """List available expirations"""
        pass

class YahooFinanceOptionsProvider(OptionsDataProvider):
    """Fetch options from Yahoo Finance via yfinance library"""
    
    def fetch_chain(self, ticker: str, expiration: str) -> List[OptionContract]:
        """
        Args:
            ticker: Stock symbol
            expiration: Expiration date (YYYY-MM-DD format)
        
        Returns:
            List of OptionContract objects
        """
        import yfinance as yf
        
        try:
            stock = yf.Ticker(ticker)
            
            # Fetch options chain
            chain = stock.option_chain(expiration)
            calls = chain.calls
            puts = chain.puts
            
            # Get underlying price
            underlying_price = stock.info.get("currentPrice", 0)
            
            contracts = []
            
            # Process calls
            for _, row in calls.iterrows():
                contract = OptionContract(
                    ticker=ticker,
                    contract_symbol=f"{ticker} {expiration} C{row['strike']:.2f}",
                    contract_type="call",
                    expiration_date=pd.to_datetime(expiration),
                    strike_price=row["strike"],
                    current_price=row["lastPrice"],
                    bid=row["bid"],
                    ask=row["ask"],
                    last_price=row["lastPrice"],
                    volume=int(row["volume"]) if pd.notna(row["volume"]) else 0,
                    open_interest=int(row["openInterest"]) if pd.notna(row["openInterest"]) else 0,
                    delta=row["delta"],
                    gamma=row["gamma"],
                    theta=row["theta"],
                    vega=row["vega"],
                    rho=row["rho"],
                    implied_vol=row["impliedVolatility"],
                    last_updated=datetime.now()
                )
                contracts.append(contract)
            
            # Process puts
            for _, row in puts.iterrows():
                contract = OptionContract(
                    ticker=ticker,
                    contract_symbol=f"{ticker} {expiration} P{row['strike']:.2f}",
                    contract_type="put",
                    expiration_date=pd.to_datetime(expiration),
                    strike_price=row["strike"],
                    current_price=row["lastPrice"],
                    bid=row["bid"],
                    ask=row["ask"],
                    last_price=row["lastPrice"],
                    volume=int(row["volume"]) if pd.notna(row["volume"]) else 0,
                    open_interest=int(row["openInterest"]) if pd.notna(row["openInterest"]) else 0,
                    delta=row["delta"],
                    gamma=row["gamma"],
                    theta=row["theta"],
                    vega=row["vega"],
                    rho=row["rho"],
                    implied_vol=row["impliedVolatility"],
                    last_updated=datetime.now()
                )
                contracts.append(contract)
            
            return contracts
            
        except Exception as e:
            raise DataFetchError(f"Failed to fetch options chain for {ticker}: {e}")
    
    def fetch_all_expirations(self, ticker: str) -> List[str]:
        """Get list of available option expirations"""
        import yfinance as yf
        
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options  # Returns list of expiration dates
            return expirations
        except Exception as e:
            raise DataFetchError(f"Failed to fetch expirations for {ticker}: {e}")

class OptionsDataService:
    """Main service for options data management"""
    
    def __init__(self, provider: OptionsDataProvider = None, cache_ttl_hours: int = 1):
        """
        Args:
            provider: OptionsDataProvider implementation
            cache_ttl_hours: Cache TTL (options data is more volatile than stock prices)
        """
        self.provider = provider or YahooFinanceOptionsProvider()
        self.cache = {}
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
    
    def get_chain(self, ticker: str, expiration: str) -> List[OptionContract]:
        """Get options chain (with cache)"""
        cache_key = f"{ticker}_{expiration}"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                return cached_data
        
        # Fetch fresh data
        contracts = self.provider.fetch_chain(ticker, expiration)
        self.cache[cache_key] = (contracts, datetime.now())
        
        return contracts
    
    def get_expirations(self, ticker: str) -> List[str]:
        """Get list of expirations"""
        return self.provider.fetch_all_expirations(ticker)
```

## API Endpoints

### Get Options Chain

```python
# src/qlib_research/app/api/routes/options.py

from fastapi import APIRouter, Depends, HTTPException, Query
from src.qlib_research.app.services.options_data_service import OptionsDataService
from src.qlib_research.app.api.dependencies import get_options_data_service

router = APIRouter(prefix="/api/options", tags=["options"])

@router.get("/chain/{ticker}")
def get_options_chain(
    ticker: str,
    expiration: str = Query(..., description="YYYY-MM-DD"),
    strike_range_pct: float = Query(0.10, description="Strike range as % of underlying (0.10 = ±10%)"),
    options_service: OptionsDataService = Depends(get_options_data_service)
):
    """
    Get options chain for a ticker and expiration.
    
    Example: GET /api/options/chain/AAPL?expiration=2024-01-19&strike_range_pct=0.10
    
    Response:
    {
      "ticker": "AAPL",
      "underlying_price": 150.25,
      "expiration": "2024-01-19",
      "days_to_expiration": 3,
      "calls": [
        {
          "strike": 150.00,
          "bid": 1.25,
          "ask": 1.35,
          "delta": 0.52,
          "gamma": 0.018,
          "theta": -0.08,
          "vega": 0.15,
          "rho": 0.02,
          "implied_vol": 0.22,
          "volume": 1250,
          "open_interest": 8500,
          "intrinsic_value": 0.25,
          "time_value": 1.00
        }
      ],
      "puts": [...]
    }
    """
    try:
        contracts = options_service.get_chain(ticker, expiration)
        
        if not contracts:
            raise HTTPException(status_code=404, detail=f"No options found for {ticker} on {expiration}")
        
        # Filter by strike range if provided
        if strike_range_pct:
            underlying_price = contracts[0].current_price  # Placeholder
            min_strike = underlying_price * (1 - strike_range_pct)
            max_strike = underlying_price * (1 + strike_range_pct)
            contracts = [c for c in contracts if min_strike <= c.strike_price <= max_strike]
        
        # Separate calls and puts
        calls = [c for c in contracts if c.contract_type == "call"]
        puts = [c for c in contracts if c.contract_type == "put"]
        
        # Serialize
        calls_data = [{
            "strike": c.strike_price,
            "bid": c.bid,
            "ask": c.ask,
            "mid": (c.bid + c.ask) / 2,
            "delta": round(c.delta, 4),
            "gamma": round(c.gamma, 4),
            "theta": round(c.theta, 4),
            "vega": round(c.vega, 4),
            "rho": round(c.rho, 4),
            "implied_vol": round(c.implied_vol * 100, 2),  # As percentage
            "volume": c.volume,
            "open_interest": c.open_interest,
            "intrinsic_value": round(c.intrinsic_value, 2),
            "time_value": round(c.time_value, 2)
        } for c in calls]
        
        puts_data = [{
            "strike": p.strike_price,
            "bid": p.bid,
            "ask": p.ask,
            "mid": (p.bid + p.ask) / 2,
            "delta": round(p.delta, 4),
            "gamma": round(p.gamma, 4),
            "theta": round(p.theta, 4),
            "vega": round(p.vega, 4),
            "rho": round(p.rho, 4),
            "implied_vol": round(p.implied_vol * 100, 2),
            "volume": p.volume,
            "open_interest": p.open_interest,
            "intrinsic_value": round(p.intrinsic_value, 2),
            "time_value": round(p.time_value, 2)
        } for p in puts]
        
        return {
            "ticker": ticker.upper(),
            "underlying_price": contracts[0].current_price,
            "expiration": expiration,
            "days_to_expiration": contracts[0].days_to_expiration,
            "calls": calls_data,
            "puts": puts_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Get Available Expirations

```python
@router.get("/expirations/{ticker}")
def get_expirations(
    ticker: str,
    options_service: OptionsDataService = Depends(get_options_data_service)
):
    """
    Get list of available option expirations.
    
    Example: GET /api/options/expirations/AAPL
    
    Response:
    {
      "ticker": "AAPL",
      "expirations": [
        "2024-01-19",
        "2024-01-26",
        "2024-02-02",
        ...
      ]
    }
    """
    try:
        expirations = options_service.get_expirations(ticker)
        return {
            "ticker": ticker.upper(),
            "expirations": expirations
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Greeks Interpretation Guide

### Delta (Δ)
```
Meaning: Probability of expiring in-the-money (approximately)
Range: Calls 0-1, Puts -1-0
Trade-off: High delta options move like stock; low delta options are cheap
Risk/Reward: +0.5 delta call = 50% ITM probability; loses money if stock falls
```

### Gamma (Γ)
```
Meaning: How much delta changes per $1 stock move
High gamma: Delta very sensitive to price (good for volatility trading)
Trade-off: High gamma = expensive; low gamma = cheap
Risk/Reward: Buy ATM calls if expecting volatility spike (high gamma)
```

### Theta (Θ)
```
Meaning: Time decay (loses this much per day)
Negative for long options (you lose money as time passes)
Positive for short options (you make money as time passes)
Trade-off: Sell time decay (short calls) vs buy time (long calls for upside)
```

### Vega (ν)
```
Meaning: Sensitivity to 1% IV change
High vega: Option expensive in high IV; loses if IV drops
Low vega: Option cheap; IV doesn't matter much
Trade-off: Buy options in low IV (expect IV rise); sell in high IV
```

### Rho (ρ)
```
Meaning: Sensitivity to interest rate changes
Usually small for short-dated options
Matters more for long-term options or in rising rate environment
```

## UI Display

### Options Chain Table
```
Show columns: Strike | Bid | Ask | Delta | Gamma | Theta | Vega | IV% | Volume | OI

Color coding:
- ATM (±5% of underlying): Highlight in blue
- ITM: Highlight in green
- OTM: Highlight in gray
- High volume: Bold text

Interactive:
- Click on strike: Show detailed Greeks breakdown
- Hover on Greeks: Tooltip with interpretation
- Toggle calls/puts: Switch between calls and puts table
```

### Greeks Legend
```
Delta: Directional exposure (stock correlation)
Gamma: Gamma convexity (acceleration)
Theta: Daily time decay
Vega: IV sensitivity
IV%: Implied volatility (%)
```

## Caching Strategy

- **Cache TTL**: 1 hour (options data more volatile than stocks)
- **Manual refresh**: Button to force refresh specific expiration
- **Scheduled**: Refresh main expirations (weekly, monthly, quarterly) at market open

## Testing

```python
# tests/unit/test_greeks_calculator.py

def test_black_scholes_call():
    """Test Black-Scholes pricing for call option"""
    price = GreeksCalculator.black_scholes_price(
        S=100, K=100, T=0.25, r=0.05, sigma=0.2, option_type="call"
    )
    assert 5 < price < 10  # Should be in reasonable range

def test_delta():
    """Test delta calculation"""
    delta = GreeksCalculator.delta(
        S=100, K=100, T=0.25, r=0.05, sigma=0.2, option_type="call"
    )
    assert 0 < delta < 1  # Call delta between 0 and 1

def test_implied_vol():
    """Test implied volatility solver"""
    market_price = 10.0
    iv = ImpliedVolatilityCalculator.implied_vol(
        market_price=market_price,
        S=100, K=100, T=0.25, r=0.05, option_type="call"
    )
    assert iv is not None
    assert 0.01 < iv < 2.0  # Should be reasonable IV
```

## Acceptance Criteria

- [ ] Options chain fetches from Yahoo Finance or external API
- [ ] Black-Scholes Greeks computed correctly (validate against market data)
- [ ] IV solver works (implied vol matches market levels)
- [ ] API endpoint returns options chain with Greeks
- [ ] Expirations endpoint returns list of available dates
- [ ] Cache works (1-hour TTL, manual refresh)
- [ ] UI displays chain with strike, Greeks, bid/ask
- [ ] ATM strikes highlighted
- [ ] No order entry (display only)
- [ ] Handle missing data gracefully

## Known Limitations (MVP)

- **Read-only**: No order entry until data source validated
- **Daily update**: Not real-time (refresh on market close)
- **US equities only**: No index or futures options
- **Simplified Greeks**: Black-Scholes only (no local vol, jumps, etc.)
- **No spreads**: Cannot visualize multi-leg strategies yet
- **No position Greeks**: Cannot aggregate Greeks across holdings
