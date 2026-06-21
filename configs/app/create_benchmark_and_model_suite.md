# Create Benchmark and Model Suite Specification
# Establish baseline models and comparison framework

## Overview

Build comparison baseline:
1. **Naive models** — Buy-hold, momentum baseline, 50-50
2. **Simple models** — SMA crossover, RSI-based
3. **Ensemble** — Combine signals
4. **Track metrics** — Compare Sharpe, win rate, DD

## Implementation

```python
# src/qlib_research/models/benchmarks.py

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Tuple

@dataclass
class BacktestResult:
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    total_return: float
    trades: int

class BuyHoldBenchmark:
    """Baseline: buy and hold SPY"""
    
    def backtest(self, prices: pd.DataFrame, start: str, end: str) -> BacktestResult:
        subset = prices.loc[start:end]
        returns = subset['SPY'].pct_change()
        
        total_return = (1 + returns).prod() - 1
        sharpe = returns.mean() / returns.std() * np.sqrt(252)
        
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = cumulative / running_max - 1
        max_dd = drawdown.min()
        
        return BacktestResult(
            win_rate=0.5,  # Neutral
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            total_return=total_return,
            trades=1  # One buy at start
        )

class SMAcrossover:
    """Simple moving average crossover"""
    
    def __init__(self, fast_period=20, slow_period=50):
        self.fast = fast_period
        self.slow = slow_period
    
    def generate_signals(self, prices: pd.DataFrame) -> pd.Series:
        """Generate BUY/SELL signals"""
        
        fast_ma = prices['close'].rolling(self.fast).mean()
        slow_ma = prices['close'].rolling(self.slow).mean()
        
        signals = pd.Series(0, index=prices.index)
        signals[fast_ma > slow_ma] = 1  # BUY
        signals[fast_ma < slow_ma] = -1  # SELL
        
        return signals
    
    def backtest(self, prices: pd.DataFrame, start: str, end: str) -> BacktestResult:
        signals = self.generate_signals(prices)
        returns = prices['close'].pct_change()
        
        # PnL from signals
        signal_returns = signals.shift(1) * returns
        
        # Metrics
        cumulative = (1 + signal_returns).cumprod()
        total_return = cumulative.iloc[-1] - 1
        sharpe = signal_returns.mean() / signal_returns.std() * np.sqrt(252)
        
        running_max = cumulative.expanding().max()
        drawdown = cumulative / running_max - 1
        max_dd = drawdown.min()
        
        win_trades = (signal_returns > 0).sum()
        total_trades = (signals.diff() != 0).sum()
        win_rate = win_trades / max(total_trades, 1)
        
        return BacktestResult(
            win_rate=win_rate,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            total_return=total_return,
            trades=total_trades
        )

class RSIStrategy:
    """Relative Strength Index strategy"""
    
    def __init__(self, period=14, overbought=70, oversold=30):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def generate_signals(self, prices: pd.DataFrame) -> pd.Series:
        """RSI overbought/oversold signals"""
        
        delta = prices['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        signals = pd.Series(0, index=prices.index)
        signals[rsi < self.oversold] = 1  # BUY (oversold)
        signals[rsi > self.overbought] = -1  # SELL (overbought)
        
        return signals
    
    def backtest(self, prices: pd.DataFrame, start: str, end: str) -> BacktestResult:
        # Similar to SMA backtest
        pass

class EnsembleSignal:
    """Combine multiple strategies"""
    
    def __init__(self, strategies: list):
        self.strategies = strategies
    
    def generate_signals(self, prices: pd.DataFrame) -> pd.Series:
        """Ensemble vote"""
        
        signals = pd.DataFrame()
        for name, strategy in self.strategies:
            signals[name] = strategy.generate_signals(prices)
        
        # Majority vote
        ensemble = signals.mean()
        ensemble_signal = pd.Series(0, index=prices.index)
        ensemble_signal[ensemble > 0.5] = 1
        ensemble_signal[ensemble < -0.5] = -1
        
        return ensemble_signal
    
    def backtest(self, prices: pd.DataFrame, start: str, end: str) -> BacktestResult:
        signals = self.generate_signals(prices)
        returns = prices['close'].pct_change()
        
        signal_returns = signals.shift(1) * returns
        
        cumulative = (1 + signal_returns).cumprod()
        total_return = cumulative.iloc[-1] - 1
        sharpe = signal_returns.mean() / signal_returns.std() * np.sqrt(252)
        
        running_max = cumulative.expanding().max()
        drawdown = cumulative / running_max - 1
        max_dd = drawdown.min()
        
        win_trades = (signal_returns > 0).sum()
        total_trades = (signals.diff() != 0).sum()
        win_rate = win_trades / max(total_trades, 1)
        
        return BacktestResult(
            win_rate=win_rate,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            total_return=total_return,
            trades=total_trades
        )

class BenchmarkComparison:
    """Compare models against benchmarks"""
    
    def __init__(self, prices: pd.DataFrame):
        self.prices = prices
        self.benchmarks = {
            'buy_hold': BuyHoldBenchmark(),
            'sma_20_50': SMAcrossover(20, 50),
            'sma_50_200': SMAcrossover(50, 200),
            'rsi_14': RSIStrategy(),
            'ensemble': EnsembleSignal([
                ('sma_20_50', SMAcrossover(20, 50)),
                ('rsi_14', RSIStrategy())
            ])
        }
    
    def run_all(self, start: str, end: str) -> dict:
        """Backtest all benchmarks"""
        
        results = {}
        
        for name, model in self.benchmarks.items():
            try:
                result = model.backtest(self.prices, start, end)
                results[name] = {
                    'win_rate': f"{result.win_rate:.0%}",
                    'sharpe': f"{result.sharpe_ratio:.2f}",
                    'max_dd': f"{result.max_drawdown:.0%}",
                    'total_return': f"{result.total_return:.0%}",
                    'trades': result.trades
                }
            except Exception as e:
                results[name] = {'error': str(e)}
        
        return results
```

## Acceptance Criteria

- [ ] Buy-hold baseline implemented
- [ ] SMA crossover implemented
- [ ] RSI strategy implemented
- [ ] Ensemble voting working
- [ ] Comparison framework working
- [ ] Backtest metrics calculated
- [ ] All benchmarks pass tests
