# tests/unit/test_features.py
"""Unit tests for feature engineering pipeline."""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from src.qlib_research.app.services.feature_pipeline import (
    FeaturePipeline,
    FeatureConfig,
    TrendIndicators,
    MomentumIndicators,
    VolatilityIndicators,
    VolumeIndicators,
    TargetEngineering,
    FeatureScaler,
    get_feature_matrix
)


@pytest.fixture
def sample_ohlcv():
    """Create sample OHLCV data."""
    dates = pd.date_range('2024-01-01', periods=100)
    
    np.random.seed(42)
    closes = 100 + np.cumsum(np.random.randn(100) * 2)
    
    df = pd.DataFrame({
        'open': closes + np.random.randn(100),
        'high': closes + np.abs(np.random.randn(100)) + 1,
        'low': closes - np.abs(np.random.randn(100)) - 1,
        'close': closes,
        'volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)
    
    return df


class TestTrendIndicators:
    """Test trend indicators."""
    
    def test_sma(self, sample_ohlcv):
        """Test Simple Moving Average."""
        sma = TrendIndicators.sma(sample_ohlcv['close'], 20)
        
        assert len(sma) == len(sample_ohlcv)
        assert sma.isna().sum() == 19  # First 19 values should be NaN
        assert not sma.iloc[20:].isna().any()  # Rest should be valid
    
    def test_ema(self, sample_ohlcv):
        """Test Exponential Moving Average."""
        ema = TrendIndicators.ema(sample_ohlcv['close'], 12)
        
        assert len(ema) == len(sample_ohlcv)
        assert not ema.isna().any()
        
        # EMA should be close to but not equal to SMA
        sma = TrendIndicators.sma(sample_ohlcv['close'], 12)
        assert not ema.equals(sma)
    
    def test_macd(self, sample_ohlcv):
        """Test MACD."""
        macd, signal, hist = TrendIndicators.macd(sample_ohlcv['close'])
        
        assert len(macd) == len(sample_ohlcv)
        assert len(signal) == len(sample_ohlcv)
        assert len(hist) == len(sample_ohlcv)
        
        # Histogram should be MACD - Signal
        assert np.allclose(hist.dropna(), (macd - signal).dropna(), rtol=1e-5)


class TestMomentumIndicators:
    """Test momentum indicators."""
    
    def test_rsi(self, sample_ohlcv):
        """Test RSI."""
        rsi = MomentumIndicators.rsi(sample_ohlcv['close'], 14)
        
        assert len(rsi) == len(sample_ohlcv)
        
        # RSI should be between 0 and 100
        assert rsi.min() >= 0
        assert rsi.max() <= 100
    
    def test_momentum(self, sample_ohlcv):
        """Test momentum."""
        momentum = MomentumIndicators.momentum(sample_ohlcv['close'], 10)
        
        assert len(momentum) == len(sample_ohlcv)
        assert momentum.isna().sum() == 10  # First 10 values should be NaN
    
    def test_roc(self, sample_ohlcv):
        """Test Rate of Change."""
        roc = MomentumIndicators.roc(sample_ohlcv['close'], 12)
        
        assert len(roc) == len(sample_ohlcv)
        assert roc.isna().sum() == 12


class TestVolatilityIndicators:
    """Test volatility indicators."""
    
    def test_bollinger_bands(self, sample_ohlcv):
        """Test Bollinger Bands."""
        upper, middle, lower = VolatilityIndicators.bollinger_bands(
            sample_ohlcv['close'],
            period=20
        )
        
        assert len(upper) == len(sample_ohlcv)
        assert len(middle) == len(sample_ohlcv)
        assert len(lower) == len(sample_ohlcv)
        
        # Upper > Middle > Lower
        valid_idx = ~(upper.isna() | middle.isna() | lower.isna())
        assert (upper[valid_idx] > middle[valid_idx]).all()
        assert (middle[valid_idx] > lower[valid_idx]).all()
    
    def test_atr(self, sample_ohlcv):
        """Test Average True Range."""
        atr = VolatilityIndicators.atr(
            sample_ohlcv['high'],
            sample_ohlcv['low'],
            sample_ohlcv['close'],
            period=14
        )
        
        assert len(atr) == len(sample_ohlcv)
        assert atr[atr.notna()].min() > 0
    
    def test_historical_volatility(self, sample_ohlcv):
        """Test historical volatility."""
        returns = sample_ohlcv['close'].pct_change()
        hv = VolatilityIndicators.historical_volatility(returns, 20)
        
        assert len(hv) == len(sample_ohlcv)
        assert hv[hv.notna()].min() > 0


class TestVolumeIndicators:
    """Test volume indicators."""
    
    def test_obv(self, sample_ohlcv):
        """Test On-Balance Volume."""
        obv = VolumeIndicators.on_balance_volume(
            sample_ohlcv['close'],
            sample_ohlcv['volume']
        )
        
        assert len(obv) == len(sample_ohlcv)
        # OBV should be monotonic (generally increasing or decreasing)
        assert not obv.isna().any()
    
    def test_volume_ratio(self, sample_ohlcv):
        """Test volume ratio."""
        vol_ratio = VolumeIndicators.volume_ratio(sample_ohlcv['volume'], 20)
        
        assert len(vol_ratio) == len(sample_ohlcv)
        assert vol_ratio[vol_ratio.notna()].min() >= 0


class TestTargetEngineering:
    """Test target engineering."""
    
    def test_forward_returns(self, sample_ohlcv):
        """Test forward returns calculation."""
        returns = TargetEngineering.forward_returns(
            sample_ohlcv['close'],
            [1, 5, 20]
        )
        
        assert 'ret_1' in returns
        assert 'ret_5' in returns
        assert 'ret_20' in returns
        
        for key, ret in returns.items():
            assert len(ret) == len(sample_ohlcv)
            # Last N values should be NaN (no future data)
            assert ret.isna().sum() > 0
    
    def test_classification_labels(self, sample_ohlcv):
        """Test classification labels."""
        returns = TargetEngineering.forward_returns(
            sample_ohlcv['close'],
            [1]
        )['ret_1']
        
        labels = TargetEngineering.classification_labels(returns, threshold=0.01)
        
        assert len(labels) == len(sample_ohlcv)
        # Labels should be -1, 0, or 1
        assert set(labels.dropna().unique()).issubset({-1, 0, 1})
    
    def test_return_bins(self, sample_ohlcv):
        """Test return binning."""
        returns = TargetEngineering.forward_returns(
            sample_ohlcv['close'],
            [5]
        )['ret_5']
        
        bins = TargetEngineering.return_bins(returns.dropna(), bins=5)
        
        # Should have bins from 0 to 4 (or fewer if duplicates merged)
        assert bins.max() >= 0
        assert bins.min() >= 0


class TestFeaturePipeline:
    """Test complete feature pipeline."""
    
    def test_engineer_features(self, sample_ohlcv):
        """Test feature engineering."""
        pipeline = FeaturePipeline()
        features = pipeline.engineer_features(sample_ohlcv)
        
        # Should have more columns than original
        assert len(features.columns) > len(sample_ohlcv.columns)
        
        # Check some expected columns
        assert 'sma_5' in features.columns
        assert 'ema_12' in features.columns
        assert 'rsi' in features.columns
        assert 'macd' in features.columns
    
    def test_engineer_targets(self, sample_ohlcv):
        """Test target engineering."""
        pipeline = FeaturePipeline()
        targets = pipeline.engineer_targets(sample_ohlcv)
        
        assert 'ret_1' in targets
        assert 'ret_5' in targets
        assert 'label_1d' in targets
    
    def test_get_stats(self, sample_ohlcv):
        """Test pipeline statistics."""
        pipeline = FeaturePipeline()
        pipeline.engineer_features(sample_ohlcv)
        
        stats = pipeline.get_stats()
        
        assert 'features_created' in stats
        assert 'targets_created' in stats
        assert 'error_count' in stats
        assert stats['features_created'] > 0


class TestFeatureScaler:
    """Test feature scaling."""
    
    def test_normalize(self, sample_ohlcv):
        """Test normalization."""
        df = sample_ohlcv[['close']].copy()
        scaled = FeatureScaler.normalize(df, ['close'])
        
        # Should be in [0, 1]
        assert scaled['close'].min() >= 0
        assert scaled['close'].max() <= 1
    
    def test_standardize(self, sample_ohlcv):
        """Test standardization."""
        df = sample_ohlcv[['close']].copy()
        scaled = FeatureScaler.standardize(df, ['close'])
        
        # Mean should be ~0, std should be ~1
        assert abs(scaled['close'].mean()) < 0.1
        assert abs(scaled['close'].std() - 1) < 0.1


class TestGetFeatureMatrix:
    """Test convenience function."""
    
    def test_get_feature_matrix(self, sample_ohlcv):
        """Test feature matrix generation."""
        features, targets = get_feature_matrix(sample_ohlcv)
        
        assert len(features) < len(sample_ohlcv)  # Some rows dropped due to NaN
        assert len(targets) > 0
        assert 'ret_1' in targets
