# Feature and Processor Pipeline Specification
# Build reusable feature engineering for Qlib signals

## Overview

Pipeline for feature computation:
1. **Raw OHLCV** from market data
2. **Technical indicators** (SMA, RSI, MACD, Bollinger)
3. **Advanced features** (momentum, mean reversion)
4. **Target engineering** (forward returns)
5. **Scaling and encoding**

## Architecture

```python
# src/qlib_research/features/processor_pipeline.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
import pandas as pd
import numpy as np
from typing import List, Optional

@dataclass
class FeatureSpec:
    """Feature definition"""
    name: str
    category: str         # "technical", "momentum", "mean_reversion"
    lookback: int         # Days to look back
    params: dict          # Indicator parameters

class FeatureProcessor(ABC):
    """Base feature processor"""
    
    @abstractmethod
    def compute(self, ohlcv: pd.DataFrame) -> pd.DataFrame:
        """Compute feature from OHLCV"""
        pass

class SMAProcessor(FeatureProcessor):
    """Simple moving average features"""
    
    def __init__(self, periods: List[int] = None):
        self.periods = periods or [20, 50, 200]
    
    def compute(self, ohlcv: pd.DataFrame) -> pd.DataFrame:
        """SMA features"""
        
        features = pd.DataFrame(index=ohlcv.index)
        
        for period in self.periods:
            features[f'SMA_{period}'] = ohlcv['close'].rolling(period).mean()
        
        # Price vs SMA ratios
        features['close_vs_SMA50'] = ohlcv['close'] / ohlcv['close'].rolling(50).mean()
        
        return features

class RSIProcessor(FeatureProcessor):
    """Relative Strength Index"""
    
    def compute(self, ohlcv: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """RSI feature"""
        
        delta = ohlcv['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return pd.DataFrame({'RSI_14': rsi}, index=ohlcv.index)

class MomentumProcessor(FeatureProcessor):
    """Momentum and trend features"""
    
    def compute(self, ohlcv: pd.DataFrame) -> pd.DataFrame:
        """Momentum features"""
        
        features = pd.DataFrame(index=ohlcv.index)
        
        # Momentum
        for period in [5, 10, 20]:
            features[f'momentum_{period}'] = (
                ohlcv['close'] - ohlcv['close'].shift(period)
            ) / ohlcv['close'].shift(period)
        
        # ROC (Rate of Change)
        features['ROC_10'] = (
            (ohlcv['close'] - ohlcv['close'].shift(10)) / ohlcv['close'].shift(10)
        )
        
        # MACD
        ema12 = ohlcv['close'].ewm(span=12).mean()
        ema26 = ohlcv['close'].ewm(span=26).mean()
        features['MACD'] = ema12 - ema26
        features['MACD_signal'] = features['MACD'].ewm(span=9).mean()
        
        return features

class VolatilityProcessor(FeatureProcessor):
    """Volatility features"""
    
    def compute(self, ohlcv: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """Volatility features"""
        
        features = pd.DataFrame(index=ohlcv.index)
        
        # Historical volatility (close-to-close)
        returns = ohlcv['close'].pct_change()
        features['volatility_20'] = returns.rolling(period).std()
        
        # Parkinson volatility (OHLC range)
        high_low = np.log(ohlcv['high'] / ohlcv['low'])
        features['parkinson_vol'] = (1 / (4 * np.log(2))) * (high_low ** 2).rolling(period).mean() ** 0.5
        
        # Bollinger Bands
        sma = ohlcv['close'].rolling(period).mean()
        std = ohlcv['close'].rolling(period).std()
        features['BB_upper'] = sma + (std * 2)
        features['BB_lower'] = sma - (std * 2)
        features['BB_position'] = (
            (ohlcv['close'] - features['BB_lower']) / 
            (features['BB_upper'] - features['BB_lower'])
        )
        
        return features

class MeanReversionProcessor(FeatureProcessor):
    """Mean reversion features"""
    
    def compute(self, ohlcv: pd.DataFrame) -> pd.DataFrame:
        """Mean reversion features"""
        
        features = pd.DataFrame(index=ohlcv.index)
        
        # Z-score (distance from mean in std devs)
        for period in [20, 50]:
            close_mean = ohlcv['close'].rolling(period).mean()
            close_std = ohlcv['close'].rolling(period).std()
            features[f'z_score_{period}'] = (
                (ohlcv['close'] - close_mean) / close_std
            )
        
        # Deviation from trend
        sma_50 = ohlcv['close'].rolling(50).mean()
        features['deviation_from_ma50'] = (
            ohlcv['close'] - sma_50
        ) / sma_50
        
        return features

class VolumeProcessor(FeatureProcessor):
    """Volume features"""
    
    def compute(self, ohlcv: pd.DataFrame) -> pd.DataFrame:
        """Volume features"""
        
        features = pd.DataFrame(index=ohlcv.index)
        
        # Volume SMA
        features['volume_SMA_20'] = ohlcv['volume'].rolling(20).mean()
        features['volume_ratio'] = ohlcv['volume'] / features['volume_SMA_20']
        
        # On-Balance Volume
        sign = (ohlcv['close'].diff() > 0).astype(int) * 2 - 1
        obv = (sign * ohlcv['volume']).fillna(0).cumsum()
        features['OBV'] = obv
        
        return features

class TargetProcessor(FeatureProcessor):
    """Target/label engineering"""
    
    def compute(
        self,
        ohlcv: pd.DataFrame,
        lookahead_days: int = 5,
        threshold_pct: float = 0.02
    ) -> pd.DataFrame:
        """Create binary classification target"""
        
        # Forward return
        forward_return = (
            ohlcv['close'].shift(-lookahead_days) / ohlcv['close']
        ) - 1
        
        # Binary: 1 if up >threshold, 0 if down
        target = (forward_return > threshold_pct).astype(int)
        
        return pd.DataFrame({'target': target}, index=ohlcv.index)

class FeaturePipeline:
    """Assemble all processors"""
    
    def __init__(self):
        self.processors = [
            ('sma', SMAProcessor()),
            ('rsi', RSIProcessor()),
            ('momentum', MomentumProcessor()),
            ('volatility', VolatilityProcessor()),
            ('mean_reversion', MeanReversionProcessor()),
            ('volume', VolumeProcessor())
        ]
    
    def compute_features(
        self,
        ohlcv: pd.DataFrame,
        include_target: bool = True,
        target_lookahead: int = 5
    ) -> pd.DataFrame:
        """Compute all features"""
        
        features = ohlcv.copy()
        
        # Compute each feature set
        for name, processor in self.processors:
            try:
                proc_features = processor.compute(ohlcv)
                features = features.join(proc_features, how='inner')
            except Exception as e:
                print(f"Error computing {name}: {e}")
        
        # Target
        if include_target:
            target = TargetProcessor().compute(ohlcv, target_lookahead)
            features = features.join(target, how='inner')
        
        # Drop NaNs (from rolling window)
        features = features.dropna()
        
        return features
```

## Usage

```python
# In training notebook

from src.qlib_research.features.processor_pipeline import FeaturePipeline

# Initialize
pipeline = FeaturePipeline()

# For each ticker, compute features
ohlcv = market_data.get_ohlcv('AAPL', start_date='2023-01-01', end_date='2024-01-01')

features = pipeline.compute_features(
    ohlcv=ohlcv,
    include_target=True,
    target_lookahead=5
)

# features now has ~50 features + target
# Ready for LightGBM training
```

## Acceptance Criteria

- [ ] SMA processor working
- [ ] RSI processor working
- [ ] Momentum processor working
- [ ] Volatility processor working
- [ ] Mean reversion processor working
- [ ] Volume processor working
- [ ] Target processor working
- [ ] Pipeline integrates all
- [ ] No NaN leakage
- [ ] Unit tests pass
