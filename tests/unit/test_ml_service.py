# tests/unit/test_ml_service.py
"""Unit tests for ML training service."""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from src.qlib_research.app.services.ml_service import (
    ModelConfig,
    ModelTrainer,
    TimeSeriesDataSplit,
    BacktestEngine
)
from src.qlib_research.app.services.feature_pipeline import (
    FeaturePipeline, FeatureConfig
)


@pytest.fixture
def sample_ohlcv():
    """Create sample OHLCV data."""
    dates = pd.date_range('2023-01-01', periods=500)
    
    np.random.seed(42)
    closes = 100 + np.cumsum(np.random.randn(500) * 2)
    
    df = pd.DataFrame({
        'open': closes + np.random.randn(500),
        'high': closes + np.abs(np.random.randn(500)) + 1,
        'low': closes - np.abs(np.random.randn(500)) - 1,
        'close': closes,
        'volume': np.random.randint(1000000, 5000000, 500)
    }, index=dates)
    
    return df


class TestModelConfig:
    """Test model configuration."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = ModelConfig()
        
        assert config.model_family == "lightgbm"
        assert config.task == "classification"
        assert config.target_column == "label_1d"
        assert config.n_splits == 5
        assert config.params['num_leaves'] == 31
    
    def test_config_serialization(self):
        """Test configuration serialization."""
        config = ModelConfig(model_family="random_forest", task="regression", forecast_horizon=5, n_estimators=200)
        
        config_dict = config.to_dict()
        
        assert config_dict['model_family'] == "random_forest"
        assert config_dict['task'] == "regression"
        assert config_dict['target_column'] == "ret_5"
        assert config_dict['params']['n_estimators'] == 200


class TestTimeSeriesDataSplit:
    """Test time-series data splitter."""
    
    def test_split_basic(self, sample_ohlcv):
        """Test basic splitting."""
        splitter = TimeSeriesDataSplit(n_splits=5)
        
        splits = list(splitter.split(sample_ohlcv))
        
        assert len(splits) == 5
        
        # Check that splits don't overlap
        for i, (train_idx, test_idx) in enumerate(splits):
            assert len(train_idx) > 0
            assert len(test_idx) > 0
            assert len(np.intersect1d(train_idx, test_idx)) == 0
    
    def test_split_temporal_order(self, sample_ohlcv):
        """Test that splits maintain temporal order."""
        splitter = TimeSeriesDataSplit(n_splits=5)
        
        splits = list(splitter.split(sample_ohlcv))
        
        for i, (train_idx, test_idx) in enumerate(splits):
            # Train should come before test
            if i > 0:
                _, prev_test_idx = splits[i-1]
                assert train_idx[-1] < test_idx[0]


class TestModelTrainer:
    """Test model trainer."""

    @pytest.mark.parametrize("model_family", ["lightgbm", "random_forest", "extra_trees"])
    def test_train_supported_model_families(self, sample_ohlcv, model_family):
        """Test supported model families train successfully."""
        config = ModelConfig(model_family=model_family, task="classification", n_estimators=10)
        trainer = ModelTrainer(config)

        X_train, y_train, X_test, y_test = trainer.prepare_data(sample_ohlcv, test_size=0.2)

        metrics = trainer.train(X_train, y_train, X_test, y_test)

        assert metrics['n_estimators'] > 0
        assert trainer.model is not None
    
    def test_prepare_data(self, sample_ohlcv):
        """Test data preparation."""
        config = ModelConfig()
        trainer = ModelTrainer(config)
        
        X_train, y_train, X_test, y_test = trainer.prepare_data(sample_ohlcv, test_size=0.2)
        
        assert len(X_train) > 0
        assert len(X_test) > 0
        assert len(X_train) > len(X_test)
        assert len(X_train) + len(X_test) <= len(sample_ohlcv)
        assert len(X_train) == len(y_train)
        assert len(X_test) == len(y_test)
    
    def test_train_classification(self, sample_ohlcv):
        """Test classification training."""
        config = ModelConfig(task="classification", n_estimators=10)
        trainer = ModelTrainer(config)
        
        X_train, y_train, X_test, y_test = trainer.prepare_data(sample_ohlcv, test_size=0.2)
        
        metrics = trainer.train(X_train, y_train, X_test, y_test)
        
        assert metrics['n_estimators'] > 0
        assert 'feature_importance' in metrics
        assert len(metrics['feature_importance']) > 0
    
    def test_predict(self, sample_ohlcv):
        """Test predictions."""
        config = ModelConfig(task="classification", n_estimators=10)
        trainer = ModelTrainer(config)
        
        X_train, y_train, X_test, y_test = trainer.prepare_data(sample_ohlcv, test_size=0.2)
        
        trainer.train(X_train, y_train, X_test, y_test)
        
        predictions = trainer.predict(X_test)
        
        assert len(predictions) == len(X_test)
    
    def test_cross_validate(self, sample_ohlcv):
        """Test cross-validation."""
        config = ModelConfig(task="classification", n_splits=3, n_estimators=5)
        trainer = ModelTrainer(config)
        
        X_train, y_train, X_test, y_test = trainer.prepare_data(sample_ohlcv, test_size=0.2)
        X_full = pd.concat([X_train, X_test])
        y_full = pd.concat([y_train, y_test])
        
        cv_results = trainer.cross_validate(X_full, y_full)
        
        assert cv_results['n_folds'] == 3
        assert len(cv_results['results_per_fold']) == 3
        assert 'mean_metrics' in cv_results
        assert 'std_metrics' in cv_results
    
    def test_feature_importance(self, sample_ohlcv):
        """Test feature importance extraction."""
        config = ModelConfig(task="classification", n_estimators=10)
        trainer = ModelTrainer(config)
        
        X_train, y_train, X_test, y_test = trainer.prepare_data(sample_ohlcv, test_size=0.2)
        
        trainer.train(X_train, y_train, X_test, y_test)
        
        top_features = trainer.get_feature_importance(top_n=5)
        
        assert len(top_features) <= 5
        assert all(isinstance(f, (list, tuple)) and len(f) == 2 for f in top_features)
    
    def test_save_load(self, sample_ohlcv, tmp_path):
        """Test model persistence."""
        for model_family in ["lightgbm", "random_forest"]:
            config = ModelConfig(model_family=model_family, task="classification", n_estimators=5)
            trainer = ModelTrainer(config)

            X_train, y_train, X_test, y_test = trainer.prepare_data(sample_ohlcv, test_size=0.2)

            trainer.train(X_train, y_train)

            model_path = tmp_path / f"model-{model_family}{trainer.model_artifact_suffix()}"
            trainer.save(str(model_path))

            trainer2 = ModelTrainer(config)
            trainer2.load(str(model_path))

            pred1 = trainer.predict(X_test)
            pred2 = trainer2.predict(X_test)

            assert np.allclose(pred1, pred2)


class TestBacktestEngine:
    """Test backtesting engine."""
    
    def test_backtest_basic(self, sample_ohlcv):
        """Test basic backtest."""
        config = ModelConfig(task="classification", n_estimators=10)
        trainer = ModelTrainer(config)
        
        X_train, y_train, X_test, y_test = trainer.prepare_data(sample_ohlcv, test_size=0.2)
        
        trainer.train(X_train, y_train)
        
        backtester = BacktestEngine(trainer, initial_capital=100000)
        
        prices_test = sample_ohlcv['close'].loc[X_test.index]
        
        result = backtester.backtest(X_test, y_test, prices_test)
        
        assert 'total_return' in result
        assert 'sharpe_ratio' in result
        assert 'max_drawdown' in result
        assert 'win_rate' in result
        assert result['final_equity'] > 0
    
    def test_backtest_metrics(self, sample_ohlcv):
        """Test backtest metrics are reasonable."""
        config = ModelConfig(task="classification", n_estimators=10)
        trainer = ModelTrainer(config)
        
        X_train, y_train, X_test, y_test = trainer.prepare_data(sample_ohlcv, test_size=0.2)
        
        trainer.train(X_train, y_train)
        
        backtester = BacktestEngine(trainer, initial_capital=100000)
        
        prices_test = sample_ohlcv['close'].loc[X_test.index]
        
        result = backtester.backtest(X_test, y_test, prices_test)
        
        # Metrics should be valid
        assert -1 <= result['sharpe_ratio'] <= 10  # Reasonable range
        assert -1 <= result['max_drawdown'] <= 0  # Drawdown is negative
        assert 0 <= result['win_rate'] <= 1  # Win rate is percentage
