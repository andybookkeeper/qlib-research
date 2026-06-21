# src/qlib_research/app/services/ml_service.py
"""Machine learning training and inference service."""

import os
import pickle
import json
from datetime import datetime
from typing import Tuple, Dict, Optional, List
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, mean_squared_error, mean_absolute_error
)

from src.qlib_research.app.services.feature_pipeline import (
    FeaturePipeline, FeatureConfig, get_feature_matrix
)


class ModelConfig:
    """LightGBM model configuration."""
    
    def __init__(
        self,
        task: str = "classification",  # classification or regression
        target_column: str = "label_1d",
        n_splits: int = 5,
        n_estimators: int = 100,
        learning_rate: float = 0.05,
        max_depth: int = 7,
        num_leaves: int = 31,
        min_child_samples: int = 20,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        early_stopping_rounds: int = 20,
        verbose: int = -1
    ):
        self.task = task
        self.target_column = target_column
        self.n_splits = n_splits
        
        # LightGBM hyperparameters
        self.params = {
            'objective': 'multiclass' if task == 'multiclass' else ('binary' if task == 'classification' else 'regression'),
            'num_leaves': num_leaves,
            'learning_rate': learning_rate,
            'n_estimators': n_estimators,
            'max_depth': max_depth,
            'min_child_samples': min_child_samples,
            'subsample': subsample,
            'colsample_bytree': colsample_bytree,
            'verbose': verbose,
        }
        
        if task == 'multiclass':
            self.params['num_class'] = 5  # For 5-bin classification
        
        self.early_stopping_rounds = early_stopping_rounds
    
    def to_dict(self) -> Dict:
        """Serialize configuration."""
        return {
            'task': self.task,
            'target_column': self.target_column,
            'n_splits': self.n_splits,
            'early_stopping_rounds': self.early_stopping_rounds,
            'params': self.params
        }


class TimeSeriesDataSplit:
    """Time-series aware data splitter."""
    
    def __init__(self, n_splits: int = 5):
        self.n_splits = n_splits
    
    def split(self, X: pd.DataFrame) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Generate time-series split indices.
        
        Args:
            X: Features DataFrame with datetime index
        
        Yields:
            (train_idx, test_idx) tuples
        """
        n_samples = len(X)
        test_size = n_samples // (self.n_splits + 1)
        
        for i in range(1, self.n_splits + 1):
            test_start = i * test_size
            test_end = min((i + 1) * test_size, n_samples)
            
            train_idx = np.arange(0, test_start)
            test_idx = np.arange(test_start, test_end)
            
            yield train_idx, test_idx


class ModelTrainer:
    """Train and evaluate LightGBM models."""
    
    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()
        self.model = None
        self.feature_names = None
        self.metrics = {}
        self.training_history = []
    
    def prepare_data(
        self,
        ohlcv: pd.DataFrame,
        feature_config: Optional[FeatureConfig] = None,
        test_size: float = 0.2
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """
        Prepare data for training.
        
        Args:
            ohlcv: OHLCV DataFrame
            feature_config: Feature engineering config
            test_size: Fraction for test set
        
        Returns:
            (X_train, y_train, X_test, y_test)
        """
        # Engineer features and targets
        features, targets = get_feature_matrix(ohlcv, feature_config, drop_na=True)
        
        # Get target variable
        if self.config.target_column not in targets:
            raise ValueError(f"Target '{self.config.target_column}' not found in targets")
        
        y = targets[self.config.target_column]
        
        # Align X and y (use intersection of indices)
        common_idx = features.index.intersection(y.index)
        X = features.loc[common_idx]
        y = y.loc[common_idx]
        
        # Time-series split
        split_idx = int(len(X) * (1 - test_size))
        
        X_train = X.iloc[:split_idx]
        X_test = X.iloc[split_idx:]
        y_train = y.iloc[:split_idx]
        y_test = y.iloc[split_idx:]
        
        self.feature_names = X_train.columns.tolist()
        
        return X_train, y_train, X_test, y_test
    
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None
    ) -> Dict:
        """
        Train LightGBM model.
        
        Args:
            X_train: Training features
            y_train: Training target
            X_val: Validation features (optional)
            y_val: Validation target (optional)
        
        Returns:
            Training metrics
        """
        # Prepare data for LightGBM
        train_data = lgb.Dataset(
            X_train,
            label=y_train,
            feature_name=self.feature_names,
            free_raw_data=False
        )
        
        valid_sets = [train_data]
        valid_names = ['training']
        
        if X_val is not None and y_val is not None:
            val_data = lgb.Dataset(
                X_val,
                label=y_val,
                feature_name=self.feature_names,
                reference=train_data,
                free_raw_data=False
            )
            valid_sets.append(val_data)
            valid_names.append('validation')
        
        # Train model
        self.model = lgb.train(
            self.config.params,
            train_data,
            num_boost_round=self.config.params.get('n_estimators', 100),
            valid_sets=valid_sets if len(valid_sets) > 1 else None,
            valid_names=valid_names if len(valid_sets) > 1 else None
        )
        
        # Get final score
        metrics = {
            'n_estimators': self.model.num_trees(),
            'feature_importance': {}
        }
        
        try:
            importances = self.model.feature_importance()
            metrics['feature_importance'] = dict(zip(
                self.feature_names,
                importances.tolist() if hasattr(importances, 'tolist') else importances
            ))
        except:
            pass
        
        return metrics
    
    def cross_validate(
        self,
        X: pd.DataFrame,
        y: pd.Series
    ) -> Dict:
        """
        Time-series cross-validation.
        
        Args:
            X: Features
            y: Target
        
        Returns:
            CV metrics (mean and std of splits)
        """
        splitter = TimeSeriesDataSplit(self.config.n_splits)
        
        fold_results = []
        
        for fold_idx, (train_idx, test_idx) in enumerate(splitter.split(X)):
            X_train_fold = X.iloc[train_idx]
            X_test_fold = X.iloc[test_idx]
            y_train_fold = y.iloc[train_idx]
            y_test_fold = y.iloc[test_idx]
            
            # Train on fold
            self.train(X_train_fold, y_train_fold, X_test_fold, y_test_fold)
            
            # Evaluate on fold
            y_pred = self.predict(X_test_fold)
            
            fold_metrics = self._evaluate(y_test_fold, y_pred)
            fold_metrics['fold'] = fold_idx + 1
            fold_results.append(fold_metrics)
            
            self.training_history.append(fold_metrics)
        
        # Aggregate results
        metrics_df = pd.DataFrame(fold_results)
        
        result = {
            'n_folds': self.config.n_splits,
            'results_per_fold': fold_results,
            'mean_metrics': metrics_df.drop('fold', axis=1).mean().to_dict(),
            'std_metrics': metrics_df.drop('fold', axis=1).std().to_dict()
        }
        
        return result
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions.
        
        Args:
            X: Features
        
        Returns:
            Predictions
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        preds = self.model.predict(X)
        
        # For binary/multiclass, LightGBM returns shape (n_samples, n_classes)
        # Convert to class labels
        if len(preds.shape) > 1:
            return np.argmax(preds, axis=1)
        
        return preds
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Get prediction probabilities (for classification).
        
        Args:
            X: Features
        
        Returns:
            Class probabilities
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        raw_predictions = self.model.predict(X, raw_score=True)
        
        if self.config.task == 'classification':
            # Softmax for multi-class
            probs = np.exp(raw_predictions) / np.sum(np.exp(raw_predictions), axis=1, keepdims=True)
            return probs
        
        return raw_predictions
    
    def _evaluate(self, y_true: pd.Series, y_pred: np.ndarray) -> Dict:
        """Calculate evaluation metrics."""
        metrics = {}
        
        # Convert y_true to numpy and ensure it's integer type for classification
        if isinstance(y_true, pd.Series):
            y_true_arr = y_true.values
        else:
            y_true_arr = y_true
        
        # Ensure y_pred is 1D (class labels, not probabilities)
        if len(y_pred.shape) > 1:
            y_pred = np.argmax(y_pred, axis=1)
        
        # Convert to same type for comparison
        y_true_arr = np.asarray(y_true_arr, dtype=np.int32)
        y_pred = np.asarray(y_pred, dtype=np.int32)
        
        if self.config.task == 'classification':
            # Binary classification
            try:
                metrics['accuracy'] = float(accuracy_score(y_true_arr, y_pred))
                metrics['precision'] = float(precision_score(y_true_arr, y_pred, average='weighted', zero_division=0))
                metrics['recall'] = float(recall_score(y_true_arr, y_pred, average='weighted', zero_division=0))
                metrics['f1'] = float(f1_score(y_true_arr, y_pred, average='weighted', zero_division=0))
            except Exception as e:
                pass
        
        elif self.config.task == 'regression':
            # Regression
            try:
                metrics['mae'] = float(mean_absolute_error(y_true_arr, y_pred))
                metrics['rmse'] = float(np.sqrt(mean_squared_error(y_true_arr, y_pred)))
            except Exception as e:
                pass
        
        return metrics
    
    def save(self, path: str) -> None:
        """Save trained model."""
        model_dir = Path(path).parent
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model
        self.model.save_model(path, num_iteration=self.model.best_iteration)
        
        # Save metadata
        metadata = {
            'config': self.config.to_dict(),
            'feature_names': self.feature_names,
            'metrics': self.metrics,
            'training_date': datetime.now().isoformat(),
            'model_type': 'lightgbm'
        }
        
        metadata_path = path.replace('.txt', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def load(self, path: str) -> None:
        """Load trained model."""
        self.model = lgb.Booster(model_file=path)
        
        # Load metadata
        metadata_path = path.replace('.txt', '_metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                self.feature_names = metadata.get('feature_names')
                self.metrics = metadata.get('metrics', {})
    
    def get_feature_importance(self, top_n: int = 20) -> List[Tuple[str, float]]:
        """
        Get feature importance.
        
        Args:
            top_n: Number of top features
        
        Returns:
            List of (feature_name, importance) tuples
        """
        if self.model is None or self.feature_names is None:
            return []
        
        try:
            importances = self.model.feature_importance()
            features = self.feature_names
            
            # Sort by importance
            importance_df = pd.DataFrame({
                'feature': features,
                'importance': importances
            }).sort_values('importance', ascending=False)
            
            return [(row['feature'], float(row['importance'])) for _, row in importance_df.head(top_n).iterrows()]
        except:
            return []


class BacktestEngine:
    """Backtesting framework."""
    
    def __init__(self, model: ModelTrainer, initial_capital: float = 100000):
        self.model = model
        self.initial_capital = initial_capital
    
    def backtest(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        prices: pd.Series,
        transaction_cost: float = 0.001  # 0.1% per trade
    ) -> Dict:
        """
        Simple backtest using model predictions.
        
        Args:
            X_test: Test features
            y_test: Test targets
            prices: Price series for P&L calculation
            transaction_cost: Cost per transaction
        
        Returns:
            Backtest statistics
        """
        # Get predictions
        y_pred = self.model.predict(X_test)
        y_pred_class = np.argmax(y_pred, axis=1) if len(y_pred.shape) > 1 else y_pred
        
        # Map predictions to signals (-1, 0, 1)
        signals = y_pred_class - 1  # Assuming labels are 0, 1, 2 → -1, 0, 1
        
        # Align prices with predictions
        common_idx = X_test.index.intersection(prices.index)
        prices_aligned = prices.loc[common_idx]
        signals_aligned = pd.Series(signals, index=X_test.index).loc[common_idx]
        
        # Calculate returns
        price_returns = prices_aligned.pct_change()
        
        # Strategy returns
        strategy_returns = signals_aligned.shift(1) * price_returns  # Signal from previous period
        
        # Remove transaction costs
        trades = signals_aligned.diff().abs() > 0
        strategy_returns -= transaction_cost * trades
        
        # Calculate cumulative returns
        cumulative_returns = (1 + strategy_returns).cumprod()
        buy_hold_returns = (1 + price_returns).cumprod()
        
        # Metrics
        total_return = cumulative_returns.iloc[-1] - 1
        buy_hold_return = buy_hold_returns.iloc[-1] - 1
        
        # Sharpe ratio
        sharpe = np.sqrt(252) * strategy_returns.mean() / strategy_returns.std()
        
        # Max drawdown
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Win rate
        win_rate = (strategy_returns > 0).sum() / len(strategy_returns) if len(strategy_returns) > 0 else 0
        
        return {
            'total_return': float(total_return),
            'buy_hold_return': float(buy_hold_return),
            'excess_return': float(total_return - buy_hold_return),
            'sharpe_ratio': float(sharpe),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate),
            'num_trades': int(trades.sum()),
            'final_equity': self.initial_capital * cumulative_returns.iloc[-1]
        }
