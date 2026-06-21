# Qlib Research Layer Specification
# Feature Engineering, Model Training, Backtesting, and Signal Serving

## Overview

The Qlib research layer is responsible for:
1. **Feature Engineering**: Computing alpha factors from price data
2. **Model Training**: Supervised learning (LightGBM) and RL models
3. **Backtesting**: Offline validation before deployment
4. **Signal Generation**: Real-time predictions for paper trading
5. **Experiment Management**: Tracking models, hyperparameters, metrics

This is the **research** component of the app. It is **decoupled** from the trading app layer. Signals are served to the app via API; the app does not import Qlib training modules.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     Market Data (Qlib)                         │
│  - Daily OHLC prices from Yahoo / local provider              │
└────────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────────┐
│              Feature Engineering Pipeline                      │
│  - Compute technical factors (momentum, volatility, etc.)     │
│  - Normalize and standardize features                         │
│  - Handle look-ahead bias prevention                          │
└────────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────────┐
│               Label Generation (Target Signals)                │
│  - Forward returns (1-day, 5-day ahead)                       │
│  - Binary classification (up/down)                            │
│  - Risk-adjusted returns (Sharpe-based)                       │
└────────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────────┐
│                  Model Training                                │
│  - LightGBM (supervised learning, primary)                    │
│  - RL (reinforcement learning, optional)                      │
│  - Cross-validation with time-series split                    │
│  - Hyperparameter tuning (grid search)                        │
└────────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────────┐
│                  Backtesting Engine                            │
│  - Simulate trades using model predictions                    │
│  - Track P&L, Sharpe, max drawdown                           │
│  - Compare to benchmarks                                      │
└────────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────────┐
│              Experiment Management (MLflow)                    │
│  - Log hyperparameters, metrics, artifacts                    │
│  - Version models for reproducibility                         │
│  - Serve best model for production inference                  │
└────────────────────────────────────────────────────────────────┘
```

## Feature Engineering Pipeline

### 1. Feature Categories

#### Price-Based Features
```python
# src/qlib_research/features.py

import pandas as pd
import numpy as np
from qlib.data import D

def compute_momentum_features(ticker: str, windows: list = [5, 10, 20]) -> pd.DataFrame:
    """
    Compute momentum-based features: price changes over different periods.
    
    Args:
        ticker: Stock symbol
        windows: List of lookback periods (days)
    
    Returns:
        DataFrame with columns: mom_5d, mom_10d, mom_20d (returns %)
    """
    df = D.features([ticker], ["close"])
    
    features = pd.DataFrame(index=df.index)
    for w in windows:
        features[f"mom_{w}d"] = df["close"].pct_change(w) * 100
    
    return features

def compute_volatility_features(ticker: str, windows: list = [10, 20]) -> pd.DataFrame:
    """
    Compute volatility features: standard deviation of returns.
    
    Args:
        ticker: Stock symbol
        windows: List of lookback periods (days)
    
    Returns:
        DataFrame with columns: vol_10d, vol_20d (%)
    """
    df = D.features([ticker], ["close"])
    returns = df["close"].pct_change() * 100
    
    features = pd.DataFrame(index=df.index)
    for w in windows:
        features[f"vol_{w}d"] = returns.rolling(w).std()
    
    return features

def compute_mean_reversion_features(ticker: str, windows: list = [5, 10, 20]) -> pd.DataFrame:
    """
    Compute mean reversion features: distance from moving average.
    
    Intuition: Stocks far from their MA tend to revert.
    """
    df = D.features([ticker], ["close"])
    
    features = pd.DataFrame(index=df.index)
    for w in windows:
        ma = df["close"].rolling(w).mean()
        features[f"ma_dist_{w}d"] = (df["close"] - ma) / ma * 100
    
    return features

def compute_volume_features(ticker: str) -> pd.DataFrame:
    """
    Compute volume-based features: volume relative to average.
    """
    df = D.features([ticker], ["volume", "close"])
    
    features = pd.DataFrame(index=df.index)
    features["vol_ratio_5d"] = df["volume"] / df["volume"].rolling(5).mean()
    features["vol_ratio_20d"] = df["volume"] / df["volume"].rolling(20).mean()
    
    return features
```

#### Technical Indicators
```python
def compute_rsi(ticker: str, period: int = 14) -> pd.DataFrame:
    """Relative Strength Index"""
    df = D.features([ticker], ["close"])
    
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return pd.DataFrame({"rsi": rsi}, index=df.index)

def compute_macd(ticker: str, fast: int = 12, slow: int = 26, signal: int = 9):
    """Moving Average Convergence Divergence"""
    df = D.features([ticker], ["close"])
    
    ema_fast = df["close"].ewm(span=fast).mean()
    ema_slow = df["close"].ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    
    return pd.DataFrame({
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram
    }, index=df.index)
```

### 2. Feature Engineering Workflow

```python
class FeatureEngineer:
    """Orchestrates feature pipeline"""
    
    def __init__(self, ticker: str, start_date: str, end_date: str):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
    
    def create_feature_matrix(self) -> pd.DataFrame:
        """
        Compute all features for the ticker and date range.
        
        Returns:
            DataFrame with all features as columns, dates as index
        """
        # Start with price data
        df = D.features(
            [self.ticker],
            ["open", "high", "low", "close", "volume"],
            start_time=self.start_date,
            end_time=self.end_date
        )
        
        # Compute feature groups
        features = pd.DataFrame(index=df.index)
        features = features.join(compute_momentum_features(self.ticker))
        features = features.join(compute_volatility_features(self.ticker))
        features = features.join(compute_mean_reversion_features(self.ticker))
        features = features.join(compute_volume_features(self.ticker))
        features = features.join(compute_rsi(self.ticker))
        features = features.join(compute_macd(self.ticker))
        
        # Normalize features (0-1 scale, per feature)
        features = (features - features.mean()) / features.std()
        
        # Drop NaN rows (due to lookback windows)
        features = features.dropna()
        
        return features
```

## Label Generation

### Forward Returns as Target

```python
def generate_labels(ticker: str, df: pd.DataFrame, 
                   forward_days: int = 1, 
                   threshold: float = 0.0) -> pd.Series:
    """
    Generate binary classification labels: is the stock going up?
    
    Args:
        ticker: Stock symbol
        df: OHLC DataFrame
        forward_days: How many days ahead to predict
        threshold: Return threshold for "up" classification (default: 0% = any positive return)
    
    Returns:
        Series with 1 (up) or 0 (down) for each date
    """
    # Get tomorrow's close
    close_prices = D.features([ticker], ["close"], 
                             start_time=df.index[0], 
                             end_time=df.index[-1])
    
    # Compute forward returns
    forward_returns = close_prices.shift(-forward_days) / close_prices - 1
    
    # Binary label: 1 if return > threshold, 0 otherwise
    labels = (forward_returns > threshold).astype(int)
    
    return labels.squeeze()
```

## Model Training

### 1. LightGBM Model (Primary)

```python
# src/qlib_research/models.py

import lightgbm as lgb
import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from qlib.data import D

class StockPredictionModel:
    """Supervised learning model for stock prediction"""
    
    def __init__(self, model_name: str = "lgb_classifier_v1", **lgb_params):
        """
        Args:
            model_name: Identifier for the model
            lgb_params: LightGBM hyperparameters
        """
        self.model_name = model_name
        self.model = None
        self.feature_names = None
        
        # Default LightGBM params
        default_params = {
            "objective": "binary",
            "metric": "auc",
            "num_leaves": 63,
            "learning_rate": 0.05,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1
        }
        default_params.update(lgb_params)
        self.lgb_params = default_params
    
    def train(self, X_train: pd.DataFrame, y_train: pd.Series, 
              X_val: pd.DataFrame = None, y_val: pd.Series = None,
              num_rounds: int = 100):
        """
        Train LightGBM model with optional validation set.
        
        Args:
            X_train: Feature matrix (dates × features)
            y_train: Binary labels (1 = up, 0 = down)
            X_val: Validation features (optional)
            y_val: Validation labels (optional)
            num_rounds: Number of boosting rounds
        
        Returns:
            Trained model
        """
        # Convert to LightGBM dataset
        train_data = lgb.Dataset(X_train, label=y_train)
        
        # Validation set (optional)
        if X_val is not None and y_val is not None:
            valid_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
            valid_sets = [valid_data]
            valid_names = ["validation"]
        else:
            valid_sets = []
            valid_names = []
        
        # Train
        self.model = lgb.train(
            params=self.lgb_params,
            train_set=train_data,
            num_boost_round=num_rounds,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=[
                lgb.log_evaluation(period=10),
                lgb.early_stopping(stopping_rounds=10)
            ]
        )
        
        self.feature_names = X_train.columns.tolist()
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Generate predictions (probabilities) for new data.
        
        Args:
            X: Feature matrix (dates × features)
        
        Returns:
            Probability predictions (0-1 range)
        """
        if self.model is None:
            raise ValueError("Model not trained yet. Call train() first.")
        
        return self.model.predict(X)
    
    def feature_importance(self, top_n: int = 10) -> pd.DataFrame:
        """Get feature importance ranking"""
        importance = self.model.feature_importance()
        df = pd.DataFrame({
            "feature": self.feature_names,
            "importance": importance
        }).sort_values("importance", ascending=False)
        
        return df.head(top_n)
    
    def save(self, path: str):
        """Save model to file"""
        self.model.save_model(path)
    
    @classmethod
    def load(cls, path: str):
        """Load model from file"""
        obj = cls()
        obj.model = lgb.Booster(model_file=path)
        return obj
```

### 2. Time Series Cross-Validation

```python
def train_with_time_series_cv(X: pd.DataFrame, y: pd.Series, 
                             n_splits: int = 5,
                             test_size: int = 63):  # ~3 months
    """
    Train model with time-series cross-validation.
    
    Prevents look-ahead bias by ensuring test sets are always in the future
    relative to training sets.
    
    Args:
        X: Feature matrix
        y: Labels
        n_splits: Number of CV folds
        test_size: Size of test set (days)
    
    Yields:
        (model, train_idx, test_idx) tuples
    """
    tscv = TimeSeriesSplit(n_splits=n_splits, test_size=test_size)
    
    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        model = StockPredictionModel()
        model.train(X_train, y_train)
        
        yield model, train_idx, test_idx
```

## Backtesting

### Backtest Engine

```python
# src/qlib_research/backtest.py

from dataclasses import dataclass
import pandas as pd
import numpy as np

@dataclass
class BacktestMetrics:
    """Backtest performance metrics"""
    total_return: float      # Total return (%)
    annual_return: float     # Annualized return (%)
    sharpe_ratio: float      # Sharpe ratio (risk-adjusted return)
    max_drawdown: float      # Maximum drawdown (%)
    win_rate: float          # % of profitable trades
    num_trades: int          # Number of trades
    avg_trade_pnl: float     # Average trade P&L

class BacktestEngine:
    """Simulates trading using model predictions"""
    
    def __init__(self, initial_cash: float = 100000, 
                 commission: float = 0.001):
        self.initial_cash = initial_cash
        self.commission = commission
    
    def backtest(self, ticker: str, predictions: pd.Series, 
                actual_prices: pd.DataFrame,
                confidence_threshold: float = 0.5) -> BacktestMetrics:
        """
        Simulate trading strategy based on model predictions.
        
        Args:
            ticker: Stock symbol
            predictions: Model predictions (0-1 probabilities)
            actual_prices: DataFrame with 'close' column
            confidence_threshold: Min confidence to trade (e.g., 0.5 = 50% confidence)
        
        Returns:
            BacktestMetrics object
        """
        # Initialize portfolio
        cash = self.initial_cash
        position = 0  # Number of shares held
        avg_cost = 0
        trades = []
        portfolio_value = []
        
        # Iterate through each day
        for date, pred in predictions.items():
            if date not in actual_prices.index:
                continue
            
            close_price = actual_prices.loc[date, "close"]
            
            # Generate signal
            is_bullish = pred > confidence_threshold
            is_bearish = pred < (1 - confidence_threshold)
            
            # Execute trades
            if is_bullish and position == 0:
                # Buy signal: invest 20% of portfolio
                qty = int((cash * 0.2) / close_price)
                cost = qty * close_price * (1 + self.commission)
                
                if cost <= cash:
                    cash -= cost
                    position = qty
                    avg_cost = close_price
                    trades.append({
                        "date": date,
                        "action": "buy",
                        "qty": qty,
                        "price": close_price,
                        "cost": cost
                    })
            
            elif is_bearish and position > 0:
                # Sell signal: liquidate position
                proceeds = position * close_price * (1 - self.commission)
                pnl = proceeds - (position * avg_cost)
                
                cash += proceeds
                trades.append({
                    "date": date,
                    "action": "sell",
                    "qty": position,
                    "price": close_price,
                    "proceeds": proceeds,
                    "pnl": pnl
                })
                position = 0
            
            # Track portfolio value
            position_value = position * close_price
            total_value = cash + position_value
            portfolio_value.append(total_value)
        
        # Compute metrics
        returns = np.array(portfolio_value) / self.initial_cash - 1
        
        total_return = (portfolio_value[-1] / self.initial_cash - 1) * 100
        annual_return = total_return * (252 / len(returns))
        
        # Sharpe ratio (assuming 0% risk-free rate)
        daily_returns = np.diff(returns)
        sharpe = np.sqrt(252) * np.mean(daily_returns) / np.std(daily_returns) if np.std(daily_returns) > 0 else 0
        
        # Max drawdown
        cum_returns = np.cumprod(1 + daily_returns)
        running_max = np.maximum.accumulate(cum_returns)
        drawdown = (cum_returns - running_max) / running_max
        max_drawdown = np.min(drawdown) * 100
        
        # Win rate
        closed_trades = [t for t in trades if t["action"] == "sell"]
        win_count = sum(1 for t in closed_trades if t["pnl"] > 0)
        win_rate = (win_count / len(closed_trades) * 100) if closed_trades else 0
        
        return BacktestMetrics(
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            num_trades=len(trades),
            avg_trade_pnl=np.mean([t.get("pnl", 0) for t in closed_trades]) if closed_trades else 0
        )
```

## Experiment Management (MLflow)

### Tracking Experiments

```python
# src/qlib_research/experiments.py

import mlflow
import pandas as pd
from datetime import datetime

class ExperimentTracker:
    """Log and track experiments using MLflow"""
    
    def __init__(self, experiment_name: str = "stock_prediction"):
        mlflow.set_experiment(experiment_name)
    
    def log_training_run(self, model_name: str, hyperparams: dict, 
                        metrics: dict, artifacts: dict = None):
        """
        Log a single training experiment.
        
        Args:
            model_name: Identifier for the model
            hyperparams: Hyperparameters (logged as params)
            metrics: Performance metrics (logged as metrics)
            artifacts: Files to save (model pkl, feature importance, etc.)
        """
        with mlflow.start_run(run_name=model_name):
            # Log hyperparameters
            for key, value in hyperparams.items():
                mlflow.log_param(key, value)
            
            # Log metrics
            for key, value in metrics.items():
                mlflow.log_metric(key, value)
            
            # Log artifacts
            if artifacts:
                for artifact_name, artifact_path in artifacts.items():
                    mlflow.log_artifact(artifact_path, artifact_name)
            
            # Log metadata
            mlflow.log_param("timestamp", datetime.now().isoformat())
            mlflow.log_param("model_name", model_name)
    
    def get_best_run(self, metric_name: str = "sharpe_ratio", mode: str = "max"):
        """
        Retrieve best run by metric.
        
        Args:
            metric_name: Metric to optimize
            mode: "max" or "min"
        
        Returns:
            Best run object
        """
        client = mlflow.tracking.MlflowClient()
        experiment = mlflow.get_experiment_by_name("stock_prediction")
        
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=[f"metrics.{metric_name} {'DESC' if mode == 'max' else 'ASC'}"]
        )
        
        return runs[0] if runs else None
```

## Signal Serving

### Daily Signal Generation

```python
# src/qlib_research/signals.py

class SignalGenerator:
    """Generate trading signals from trained model"""
    
    def __init__(self, model, ticker: str):
        self.model = model
        self.ticker = ticker
    
    def generate_signal(self, feature_engineer) -> dict:
        """
        Compute latest signal for tomorrow.
        
        Returns:
            {
              "ticker": "AAPL",
              "signal": 1 (buy),  # or 0 (sell)
              "confidence": 0.72,
              "timestamp": "2024-01-15T16:00:00Z",
              "model_id": "lgb_v1"
            }
        """
        # Compute features for latest date
        features = feature_engineer.create_feature_matrix()
        latest_features = features.iloc[-1:].values
        
        # Generate prediction
        pred_prob = self.model.predict(latest_features)[0]
        
        # Convert to signal
        signal = 1 if pred_prob > 0.5 else 0
        
        return {
            "ticker": self.ticker,
            "signal": signal,  # 1 = buy, 0 = sell/hold
            "confidence": max(pred_prob, 1 - pred_prob),
            "timestamp": datetime.now().isoformat(),
            "model_id": self.model.model_name
        }
```

## Training Workflow

```python
# Example: Complete training pipeline

if __name__ == "__main__":
    import json
    
    # 1. Prepare data
    ticker = "AAPL"
    start_date = "2020-01-01"
    end_date = "2024-01-15"
    
    # 2. Feature engineering
    fe = FeatureEngineer(ticker, start_date, end_date)
    X = fe.create_feature_matrix()
    
    # 3. Generate labels
    df = D.features([ticker], ["close"], start_time=start_date, end_time=end_date)
    y = generate_labels(ticker, df, forward_days=1)
    
    # Align X and y (remove first row from X due to label shift)
    X = X[:-1]
    y = y[1:]
    
    # 4. Split train/test (temporal split)
    train_end = int(len(X) * 0.8)
    X_train, y_train = X[:train_end], y[:train_end]
    X_test, y_test = X[train_end:], y[train_end:]
    
    # 5. Train model
    model = StockPredictionModel("lgb_v1", num_leaves=31, learning_rate=0.1)
    model.train(X_train, y_train, X_test, y_test)
    
    # 6. Backtest
    predictions = model.predict(X_test)
    pred_series = pd.Series(predictions, index=X_test.index)
    actual_prices = df.loc[X_test.index]
    
    backtest_engine = BacktestEngine()
    metrics = backtest_engine.backtest(ticker, pred_series, actual_prices)
    
    # 7. Log to MLflow
    tracker = ExperimentTracker()
    hyperparams = {
        "ticker": ticker,
        "forward_days": 1,
        "num_leaves": 31,
        "learning_rate": 0.1,
        "train_size": len(X_train)
    }
    
    metrics_dict = {
        "total_return": metrics.total_return,
        "annual_return": metrics.annual_return,
        "sharpe_ratio": metrics.sharpe_ratio,
        "max_drawdown": metrics.max_drawdown,
        "win_rate": metrics.win_rate,
        "num_trades": metrics.num_trades
    }
    
    tracker.log_training_run(
        model_name="lgb_v1",
        hyperparams=hyperparams,
        metrics=metrics_dict,
        artifacts={"model": "/path/to/model.pkl"}
    )
    
    print(f"✓ Model trained and logged to MLflow")
    print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    print(f"  Win Rate: {metrics.win_rate:.1f}%")
    print(f"  Total Return: {metrics.total_return:.2f}%")
```

## Acceptance Criteria

- [ ] Feature engineering pipeline computes momentum, volatility, mean reversion
- [ ] Labels generated correctly (forward returns, no look-ahead bias)
- [ ] LightGBM model trains successfully on sample data
- [ ] Time-series cross-validation prevents look-ahead bias
- [ ] Backtest engine simulates trading and computes Sharpe, drawdown, win rate
- [ ] MLflow experiments logged with hyperparams and metrics
- [ ] Signal generator produces buy/sell signals with confidence scores
- [ ] All Qlib data access works (no errors with Yahoo provider)
- [ ] Feature engineering handles missing data gracefully
- [ ] Model predicts on new data without errors

## Testing

```python
# tests/unit/test_feature_engineering.py

def test_momentum_features():
    """Test momentum feature computation"""
    df = pd.DataFrame({
        "close": [100, 102, 105, 103, 101, 99]
    }, index=pd.date_range("2024-01-01", periods=6))
    
    features = compute_momentum_features("TEST", windows=[1, 2])
    assert "mom_1d" in features.columns
    assert "mom_2d" in features.columns
    assert not features.isnull().any().any()

# tests/unit/test_backtesting.py

def test_backtest_metrics():
    """Test backtest metric calculations"""
    predictions = pd.Series([0.6, 0.4, 0.7, 0.3], index=pd.date_range("2024-01-01", periods=4))
    prices = pd.DataFrame({
        "close": [100, 101, 102, 103]
    }, index=pd.date_range("2024-01-01", periods=4))
    
    engine = BacktestEngine()
    metrics = engine.backtest("TEST", predictions, prices)
    
    assert metrics.total_return is not None
    assert metrics.sharpe_ratio is not None
    assert metrics.num_trades > 0
```

## Known Limitations (MVP)

- **Single asset**: Train one model per stock (no multi-asset ensemble yet)
- **Daily data**: No intraday / real-time training
- **Binary classification**: Only "up vs down" (no magnitude prediction)
- **Limited features**: Basic technical indicators (no alternative data, NLP, etc.)
- **No feature interaction**: Features computed independently
- **No drift monitoring**: Models not retrained automatically on staleness
- **No RL**: RL model support deferred to phase 2
