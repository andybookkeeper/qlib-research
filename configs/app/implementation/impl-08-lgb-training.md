# LightGBM Training Baseline Implementation (impl-08)

**Status**: ✅ COMPLETE

## Summary

Production-ready ML training service with LightGBM, time-series cross-validation, backtesting engine, and model persistence. Complete pipeline from feature engineering to trading signal generation.

## Components Created

### 1. **ModelConfig** (flexible hyperparameter management)
- Predefined LightGBM parameters (learning_rate, max_depth, num_leaves, etc.)
- Support for classification, binary, and regression tasks
- Early stopping and validation configurations
- Serializable for reproducibility

### 2. **TimeSeriesDataSplit** (temporal cross-validation)
- Prevents look-ahead bias in backtests
- K-fold time-series splitting (default 5 folds)
- Ensures test data always comes after training data
- Proper train/test chronological order

### 3. **ModelTrainer** (orchestrates training workflow)

Core methods:
- `prepare_data()` - Feature engineering + target alignment + train/test split
- `train()` - Single model training with optional validation set
- `cross_validate()` - Time-series CV with fold-by-fold metrics
- `predict()` - Class predictions from trained model
- `predict_proba()` - Probability predictions for classification
- `save()` / `load()` - Model persistence with metadata
- `get_feature_importance()` - Top N features by importance

Key features:
- Automatic feature engineering (20+ indicators)
- Data validation and alignment
- Early stopping for overfitting prevention
- Comprehensive error handling

### 4. **BacktestEngine** (trading simulation)
- Converts predictions to trading signals (-1/0/1)
- Simulates portfolio performance
- Calculates key metrics:
  - Total return vs buy-and-hold
  - Sharpe ratio (risk-adjusted returns)
  - Max drawdown
  - Win rate (% profitable trades)
  - Number of trades
  - Final equity

### 5. **API Routes** (`/api/training` endpoints)
- `POST /api/training/train` - Train model on ticker/date range
- `POST /api/training/cv/{model_id}` - Time-series cross-validation
- `POST /api/training/backtest/{model_id}` - Backtest on test data
- `GET /api/training/models` - List all trained models
- `GET /api/training/models/{model_id}` - Get model metadata

### 6. **Pydantic Schemas**
- `ModelConfigSchema` - Configuration validation
- `TrainingRequest` - Training job specification
- `TrainingResult` - Model info + top features
- `CVResult` - Cross-validation metrics
- `BacktestResult` - Trading simulation results

## Key Features

### Time-Series Cross-Validation
```python
# 5-fold time-series CV
# Fold 1: train [0-100], test [100-120]
# Fold 2: train [0-120], test [120-140]
# Fold 3: train [0-140], test [140-160]
# ... prevents look-ahead bias
```

### Data Preparation Pipeline
```python
trainer = ModelTrainer(config)
X_train, y_train, X_test, y_test = trainer.prepare_data(ohlcv)
# Automatically:
# 1. Engineer 20+ technical features
# 2. Generate forward returns targets
# 3. Align indices (no misalignment)
# 4. Time-series split (80/20)
```

### Model Training
```python
# Train on 80% of data
metrics = trainer.train(X_train, y_train, X_test, y_test)
# Get feature importance
top_features = trainer.get_feature_importance(top_n=10)
```

### Cross-Validation
```python
# 5-fold temporal CV
cv_results = trainer.cross_validate(X_full, y_full)
# Returns: mean/std accuracy, F1, precision, recall per fold
```

### Backtesting
```python
backtester = BacktestEngine(trainer, initial_capital=100000)
result = backtester.backtest(X_test, y_test, prices_test)
# Returns: total_return, sharpe_ratio, max_drawdown, win_rate, etc.
```

## Acceptance Criteria ✅

- [x] LightGBM model training (classification + regression)
- [x] Time-series cross-validation (prevent look-ahead bias)
- [x] Feature importance ranking (top N features)
- [x] Model persistence (save/load with metadata)
- [x] Backtesting engine (trading simulation)
- [x] Sharpe ratio and drawdown metrics
- [x] Configuration management and validation
- [x] Error handling and recovery
- [x] 12/12 unit tests passing
- [x] API endpoints for all operations

## Test Coverage

### Unit Tests (12/12 passing) ✅

**ModelConfig**
- test_default_config ✅
- test_config_serialization ✅

**TimeSeriesDataSplit**
- test_split_basic ✅
- test_split_temporal_order ✅

**ModelTrainer**
- test_prepare_data ✅
- test_train_classification ✅
- test_predict ✅
- test_cross_validate ✅
- test_feature_importance ✅
- test_save_load ✅

**BacktestEngine**
- test_backtest_basic ✅
- test_backtest_metrics ✅

## Technical Details

### Training Workflow
1. **Input**: OHLCV data + date range
2. **Feature Engineering**: Automatic (SMA, EMA, MACD, RSI, Bollinger, ATR, OBV, etc.)
3. **Target Creation**: Forward returns (1d/5d/20d) + classification labels
4. **Data Split**: 80% train, 20% test (time-series order preserved)
5. **Model Training**: LightGBM with early stopping
6. **Validation**: Optional validation set for early stopping
7. **Output**: Trained model + feature importance

### LightGBM Configuration
```python
{
    'objective': 'binary' (or multiclass/regression),
    'num_leaves': 31,
    'learning_rate': 0.05,
    'n_estimators': 100,
    'max_depth': 7,
    'min_child_samples': 20,
    'subsample': 0.8,
    'colsample_bytree': 0.8
}
```

### Backtesting Logic
```
1. Get predictions from model
2. Convert to trading signals: [long, neutral, short]
3. Align with price series
4. Calculate daily returns: signal * price_change
5. Apply transaction costs (0.1% per trade)
6. Calculate cumulative returns
7. Compute metrics (Sharpe, drawdown, win rate)
```

### Model Persistence
```
Saved files:
- model.txt (LightGBM booster)
- model_metadata.json (config + feature_names + metrics + date)

Metadata includes:
- Configuration used
- Feature names (for prediction)
- Training metrics
- Training timestamp
```

## Non-Obvious Behaviors

1. **Time-Series Split Is Strict**
   - Test set always comes AFTER training set
   - No shuffling or randomization
   - Prevents information leakage from future

2. **Predictions Are Class Labels**
   - Binary classification returns 0/1 (not probabilities)
   - Multiclass returns 0/1/2/... (not probabilities)
   - Use `predict_proba()` for probabilities

3. **Forward Returns Create NaN**
   - Last N rows have NaN targets (no future data)
   - Automatically dropped in `prepare_data()`
   - Fewer samples available for training

4. **Early Stopping on Validation Set**
   - Requires validation data (X_val, y_val)
   - Stops if validation metric doesn't improve
   - Prevents overfitting to training data

5. **Feature Importance Is Gain-Based**
   - LightGBM uses "gain" (improvement in loss)
   - Not permutation importance (different ranking)
   - Sum of importances across all trees

## Dependencies

- `lightgbm>=3.3.0` - ML framework
- `scikit-learn>=1.0.0` - Metrics (accuracy, F1, etc.)
- `pandas>=1.5.0` - Data handling
- `numpy>=1.20.0` - Numerical ops

## Next Steps

**impl-09: Paper Broker Service**
- Order execution (match predictions to prices)
- Position tracking (entry, exit, P&L)
- Portfolio state management

## Performance Notes

- Training time: ~1-5 seconds for 500-day dataset
- Cross-validation: ~10 seconds for 5 folds
- Backtesting: ~1 second for 100-day period
- Memory: ~100MB for trained model + data

### Optimization Opportunities
- [ ] Parallel CV (train multiple folds simultaneously)
- [ ] GPU acceleration (LightGBM CUDA)
- [ ] Incremental learning (online training)
- [ ] Distributed training (multiple machines)

## Known Limitations

1. **Single Target Only**: Cannot multi-task (predict multiple targets)
2. **No Ensemble**: Single model (not random forest/stacking)
3. **No Hyperparameter Tuning**: Fixed config (no GridSearch)
4. **No Feature Selection**: All features included (multicollinearity exists)
5. **No Class Balancing**: Handles imbalanced data poorly
6. **In-Memory Models**: All models stored in RAM (not scalable)

## Future Improvements

- [ ] Hyperparameter optimization (Bayesian, Optuna)
- [ ] Ensemble methods (stacking, blending)
- [ ] SHAP explainability for predictions
- [ ] Online learning / model updates
- [ ] GPU acceleration
- [ ] Distributed training
- [ ] Model versioning in database
- [ ] A/B testing framework
- [ ] Retraining scheduler
- [ ] Model performance monitoring
