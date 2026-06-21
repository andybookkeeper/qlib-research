# src/qlib_research/app/services/feature_pipeline.py
"""Feature engineering pipeline: technical indicators and target engineering."""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass
from enum import Enum


class IndicatorType(Enum):
    """Feature indicator types."""
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    TARGET = "target"


@dataclass
class FeatureConfig:
    """Feature engineering configuration."""
    # Trend indicators
    sma_periods: List[int] = None
    ema_periods: List[int] = None
    
    # Momentum indicators
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # Volatility indicators
    bb_period: int = 20
    bb_std_dev: int = 2
    atr_period: int = 14
    
    # Target engineering
    forward_returns_periods: List[int] = None
    classification_threshold: float = 0.01  # 1% return threshold
    
    def __post_init__(self):
        if self.sma_periods is None:
            self.sma_periods = [5, 10, 20, 50]
        if self.ema_periods is None:
            self.ema_periods = [12, 26]
        if self.forward_returns_periods is None:
            self.forward_returns_periods = [1, 5, 20]


class TrendIndicators:
    """Trend-following indicators."""
    
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average."""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average."""
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD (Moving Average Convergence Divergence).
        
        Returns:
            macd_line, signal_line, histogram
        """
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram


class MomentumIndicators:
    """Momentum indicators."""
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index (RSI).
        Range: 0-100 (>70 overbought, <30 oversold)
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def momentum(data: pd.Series, period: int = 10) -> pd.Series:
        """Price momentum (current price - price N periods ago)."""
        return data - data.shift(period)
    
    @staticmethod
    def roc(data: pd.Series, period: int = 12) -> pd.Series:
        """
        Rate of Change (ROC).
        Formula: ((Close - Close N periods ago) / Close N periods ago) * 100
        """
        return ((data - data.shift(period)) / data.shift(period)) * 100


class VolatilityIndicators:
    """Volatility indicators."""
    
    @staticmethod
    def bollinger_bands(
        close: pd.Series,
        period: int = 20,
        std_dev: float = 2
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Bollinger Bands.
        
        Returns:
            upper_band, middle_band (SMA), lower_band
        """
        middle = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    @staticmethod
    def atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Average True Range (ATR).
        Measures volatility using high-low range.
        """
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def historical_volatility(returns: pd.Series, period: int = 20) -> pd.Series:
        """
        Historical volatility (standard deviation of returns).
        """
        return returns.rolling(window=period).std() * np.sqrt(252)  # Annualized


class VolumeIndicators:
    """Volume indicators."""
    
    @staticmethod
    def on_balance_volume(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        On-Balance Volume (OBV).
        Cumulative volume indicator.
        """
        obv = pd.Series(index=close.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]
        
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    
    @staticmethod
    def volume_sma(volume: pd.Series, period: int = 20) -> pd.Series:
        """Average volume over period."""
        return volume.rolling(window=period).mean()
    
    @staticmethod
    def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
        """Current volume / Average volume ratio."""
        avg_volume = volume.rolling(window=period).mean()
        return volume / avg_volume


class TargetEngineering:
    """Target variable engineering for supervised learning."""
    
    @staticmethod
    def forward_returns(
        close: pd.Series,
        periods: List[int]
    ) -> Dict[str, pd.Series]:
        """
        Calculate forward returns (look-ahead targets).
        
        Returns:
            Dict with 'ret_<period>' as keys (e.g., 'ret_1', 'ret_5', 'ret_20')
        """
        returns = {}
        
        for period in periods:
            # Forward returns: (future_price - current_price) / current_price
            future_close = close.shift(-period)
            ret = (future_close - close) / close
            
            returns[f'ret_{period}'] = ret
        
        return returns
    
    @staticmethod
    def classification_labels(
        returns: pd.Series,
        threshold: float = 0.01,
        periods: int = 1
    ) -> pd.Series:
        """
        Classification labels from forward returns.
        
        Args:
            returns: Forward returns series
            threshold: Return threshold for classification (default 1%)
            periods: Number of periods ahead (for documentation)
        
        Returns:
            Series with labels: -1 (down), 0 (neutral), 1 (up)
        """
        labels = pd.Series(0, index=returns.index, dtype=int)
        labels[returns > threshold] = 1
        labels[returns < -threshold] = -1
        
        return labels
    
    @staticmethod
    def return_bins(
        returns: pd.Series,
        bins: int = 5
    ) -> pd.Series:
        """Bin returns into quantiles for multi-class classification."""
        return pd.qcut(returns, q=bins, labels=False, duplicates='drop')


class FeaturePipeline:
    """Complete feature engineering pipeline."""
    
    def __init__(self, config: Optional[FeatureConfig] = None):
        """
        Initialize feature pipeline.
        
        Args:
            config: Feature configuration (uses defaults if None)
        """
        self.config = config or FeatureConfig()
        self.features = {}
        self.stats = {
            'features_created': 0,
            'targets_created': 0,
            'errors': []
        }
    
    def engineer_features(self, ohlcv: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer all features from OHLCV data.
        
        Args:
            ohlcv: DataFrame with columns: open, high, low, close, volume
        
        Returns:
            DataFrame with original OHLCV + engineered features
        """
        df = ohlcv.copy()
        
        try:
            # Trend indicators
            df = self._add_trend_indicators(df)
            
            # Momentum indicators
            df = self._add_momentum_indicators(df)
            
            # Volatility indicators
            df = self._add_volatility_indicators(df)
            
            # Volume indicators
            df = self._add_volume_indicators(df)
            
            # Calculate returns for target engineering
            df['returns'] = df['close'].pct_change()
            
            self.stats['features_created'] += df.shape[1] - ohlcv.shape[1]
            
        except Exception as e:
            self.stats['errors'].append(f"Feature engineering error: {str(e)}")
        
        return df
    
    def engineer_targets(self, ohlcv: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Engineer target variables for supervised learning.
        
        Args:
            ohlcv: DataFrame with 'close' column
        
        Returns:
            Dict with forward returns and classification labels
        """
        targets = {}
        
        try:
            close = ohlcv['close']
            
            # Forward returns
            forward_ret = TargetEngineering.forward_returns(
                close,
                self.config.forward_returns_periods
            )
            targets.update(forward_ret)
            
            # Classification and multi-class labels for each configured horizon
            for period in self.config.forward_returns_periods:
                return_key = f'ret_{period}'
                if return_key not in forward_ret:
                    continue

                labels = TargetEngineering.classification_labels(
                    forward_ret[return_key],
                    self.config.classification_threshold,
                    periods=period
                )
                targets[f'label_{period}d'] = labels

                bins = TargetEngineering.return_bins(forward_ret[return_key], bins=5)
                targets[f'label_{period}d_bin'] = bins
                self.stats['targets_created'] += 2
            
        except Exception as e:
            self.stats['errors'].append(f"Target engineering error: {str(e)}")
        
        return targets
    
    def _add_trend_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add trend indicators (SMA, EMA, MACD)."""
        
        # SMAs
        for period in self.config.sma_periods:
            df[f'sma_{period}'] = TrendIndicators.sma(df['close'], period)
        
        # EMAs
        for period in self.config.ema_periods:
            df[f'ema_{period}'] = TrendIndicators.ema(df['close'], period)
        
        # MACD
        macd, signal, hist = TrendIndicators.macd(
            df['close'],
            self.config.macd_fast,
            self.config.macd_slow,
            self.config.macd_signal
        )
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_hist'] = hist
        
        return df
    
    def _add_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add momentum indicators (RSI, momentum, ROC)."""
        
        # RSI
        df['rsi'] = MomentumIndicators.rsi(df['close'], self.config.rsi_period)
        
        # Momentum
        df['momentum_10'] = MomentumIndicators.momentum(df['close'], 10)
        
        # Rate of Change
        df['roc_12'] = MomentumIndicators.roc(df['close'], 12)
        
        return df
    
    def _add_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility indicators (Bollinger Bands, ATR, HV)."""
        
        # Bollinger Bands
        upper, middle, lower = VolatilityIndicators.bollinger_bands(
            df['close'],
            self.config.bb_period,
            self.config.bb_std_dev
        )
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower
        
        # ATR
        df['atr'] = VolatilityIndicators.atr(
            df['high'],
            df['low'],
            df['close'],
            self.config.atr_period
        )
        
        # Historical Volatility
        returns = df['close'].pct_change()
        df['hv_20'] = VolatilityIndicators.historical_volatility(returns, 20)
        
        return df
    
    def _add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume indicators (OBV, volume ratio)."""
        
        # On-Balance Volume
        df['obv'] = VolumeIndicators.on_balance_volume(df['close'], df['volume'])
        
        # Volume Ratio
        df['vol_ratio'] = VolumeIndicators.volume_ratio(df['volume'], 20)
        
        return df
    
    def get_stats(self) -> Dict:
        """Get pipeline statistics."""
        return {
            'features_created': self.stats['features_created'],
            'targets_created': self.stats['targets_created'],
            'error_count': len(self.stats['errors']),
            'errors': self.stats['errors']
        }


class FeatureScaler:
    """Feature normalization/standardization."""
    
    @staticmethod
    def normalize(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """Normalize columns to [0, 1] range."""
        result = df.copy()
        
        for col in columns:
            if col in result.columns:
                min_val = result[col].min()
                max_val = result[col].max()
                
                if max_val != min_val:
                    result[col] = (result[col] - min_val) / (max_val - min_val)
                else:
                    result[col] = 0
        
        return result
    
    @staticmethod
    def standardize(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """Standardize columns (zero mean, unit variance)."""
        result = df.copy()
        
        for col in columns:
            if col in result.columns:
                mean = result[col].mean()
                std = result[col].std()
                
                if std != 0:
                    result[col] = (result[col] - mean) / std
                else:
                    result[col] = 0
        
        return result


def get_feature_matrix(
    ohlcv: pd.DataFrame,
    config: Optional[FeatureConfig] = None,
    drop_na: bool = True,
    standardize: bool = True
) -> Tuple[pd.DataFrame, Dict]:
    """
    Convenience function to engineer features from OHLCV data.
    
    Args:
        ohlcv: OHLCV DataFrame
        config: Feature configuration
        drop_na: Remove rows with NaN values
        standardize: Standardize numeric features
    
    Returns:
        Tuple of (feature_matrix, target_dict)
    """
    pipeline = FeaturePipeline(config)
    
    # Engineer features
    features = pipeline.engineer_features(ohlcv)
    
    # Engineer targets
    targets = pipeline.engineer_targets(ohlcv)
    
    # Drop NaN if requested
    if drop_na:
        features = features.dropna()
    
    # Standardize numeric columns
    if standardize:
        numeric_cols = features.select_dtypes(include=[np.number]).columns.tolist()
        features = FeatureScaler.standardize(features, numeric_cols)
    
    return features, targets
