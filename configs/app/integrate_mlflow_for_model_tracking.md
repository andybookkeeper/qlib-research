# Integrate MLflow for Model Tracking Specification
# Experiment tracking, model registry, artifact storage

## MLflow Setup

```python
# src/qlib_research/models/mlflow_tracker.py

import mlflow
from pathlib import Path
import logging

logger = logging.getLogger("qlib_trading.mlflow")

class MLflowTracker:
    """Track experiments in MLflow"""
    
    def __init__(self, experiment_name: str = "qlib_trading"):
        self.experiment_name = experiment_name
        
        # Set tracking URI to local
        mlflow_dir = Path("mlruns")
        mlflow_dir.mkdir(exist_ok=True)
        
        mlflow.set_tracking_uri(f"file://{mlflow_dir.absolute()}")
        
        # Create or get experiment
        try:
            self.experiment_id = mlflow.get_experiment_by_name(
                experiment_name
            ).experiment_id
        except:
            self.experiment_id = mlflow.create_experiment(experiment_name)
    
    def start_run(self, run_name: str, tags: dict = None):
        """Start new MLflow run"""
        
        mlflow.start_run(
            experiment_id=self.experiment_id,
            run_name=run_name
        )
        
        if tags:
            mlflow.set_tags(tags)
    
    def log_params(self, params: dict):
        """Log hyperparameters"""
        mlflow.log_params(params)
    
    def log_metrics(self, metrics: dict, step: int = None):
        """Log metrics"""
        for key, value in metrics.items():
            mlflow.log_metric(key, value, step=step)
    
    def log_model(self, model, artifact_path: str):
        """Log trained model"""
        mlflow.lightgbm.log_model(
            model,
            artifact_path=artifact_path
        )
    
    def end_run(self):
        """End run"""
        mlflow.end_run()
    
    def log_backtest_results(self, results: dict):
        """Log backtest performance"""
        
        self.log_metrics({
            "backtest_sharpe": results["sharpe_ratio"],
            "backtest_win_rate": results["win_rate"],
            "backtest_max_dd": results["max_drawdown"],
            "backtest_total_return": results["total_return"]
        })
```

## Usage in Training

```python
# src/qlib_research/notebooks/train_lightgbm.py

from src.qlib_research.models.mlflow_tracker import MLflowTracker

tracker = MLflowTracker(experiment_name="LightGBM_v1")

# Training loop
for fold in range(5):
    tracker.start_run(
        run_name=f"fold_{fold}",
        tags={"model": "LightGBM", "features": "25"}
    )
    
    # Log params
    tracker.log_params({
        "num_leaves": 31,
        "learning_rate": 0.05,
        "n_estimators": 1000
    })
    
    # Train model
    model = lgb.train(params, train_data, num_boost_round=1000)
    
    # Log metrics per epoch
    for epoch in range(1000):
        train_score = model.train_score[epoch]
        val_score = model.val_score[epoch]
        
        tracker.log_metrics({
            "train_loss": train_score,
            "val_loss": val_score
        }, step=epoch)
    
    # Log model
    tracker.log_model(model, artifact_path=f"model_fold_{fold}")
    
    # Backtest
    backtest_result = backtest_engine.backtest(model)
    tracker.log_backtest_results(backtest_result)
    
    tracker.end_run()
```

## MLflow UI

```bash
# View experiments and metrics
mlflow ui --backend-store-uri file:./mlruns

# Accessible at: http://localhost:5000
```

## Acceptance Criteria

- [ ] MLflow initialized
- [ ] Experiments tracked
- [ ] Metrics logged
- [ ] Models registered
- [ ] UI accessible
- [ ] Artifact storage working
