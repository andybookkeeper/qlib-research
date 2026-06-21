# Model Promotion Policy Specification
# When to promote trained models to production signal generation

## Overview

Define rules for graduating models from backtest to live:
1. **Backtest validation** — Sharpe, win rate, drawdown thresholds
2. **Walk-forward testing** — Out-of-sample period
3. **Feature importance** — Avoid overfitting to current regime
4. **Live trial period** — Paper trading with real signals
5. **Promotion** — Mark model as "active"

## Promotion Criteria

```python
# src/qlib_research/app/services/model_promotion_engine.py

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class ModelStatus(str, Enum):
    TRAINING = "training"
    BACKTEST = "backtest"
    TRIAL = "trial"        # Paper trading
    PROMOTED = "promoted"  # Live
    RETIRED = "retired"

@dataclass
class ModelMetrics:
    """Required metrics for promotion"""
    backtest_sharpe: float = 0.0
    backtest_win_rate: float = 0.0
    backtest_max_dd: float = 0.0
    walk_forward_sharpe: float = 0.0
    feature_importance_entropy: float = 0.0  # Higher = more stable
    trial_sharpe: float = 0.0
    trial_trades: int = 0
    
    def meets_promotion_criteria(self) -> tuple[bool, list[str]]:
        """Check if model ready to promote"""
        
        issues = []
        
        # Sharpe must be >1.0
        if self.backtest_sharpe < 1.0:
            issues.append(f"Backtest Sharpe {self.backtest_sharpe:.2f} < 1.0")
        
        # Win rate must be >50%
        if self.backtest_win_rate < 0.50:
            issues.append(f"Win rate {self.backtest_win_rate:.0%} < 50%")
        
        # Max drawdown must be <-15%
        if self.backtest_max_dd < -0.15:
            issues.append(f"Max DD {self.backtest_max_dd:.0%} < -15%")
        
        # Walk-forward should be within 0.2 Sharpe of backtest
        if abs(self.walk_forward_sharpe - self.backtest_sharpe) > 0.2:
            issues.append(
                f"Walk-forward Sharpe {self.walk_forward_sharpe:.2f} "
                f"diverges from backtest {self.backtest_sharpe:.2f}"
            )
        
        # Trial period must show at least 5 trades
        if self.trial_trades < 5:
            issues.append(f"Trial trades {self.trial_trades} < 5")
        
        # Trial Sharpe should be positive or close to backtest
        if self.trial_sharpe < 0 and abs(self.trial_sharpe - self.backtest_sharpe) > 0.3:
            issues.append(
                f"Trial Sharpe {self.trial_sharpe:.2f} "
                f"significantly worse than backtest"
            )
        
        # Feature importance should be reasonably distributed (entropy > 3.0)
        if self.feature_importance_entropy < 3.0:
            issues.append(
                f"Low feature diversity (entropy {self.feature_importance_entropy:.2f}), "
                f"possible overfitting"
            )
        
        return len(issues) == 0, issues

class ModelPromotionEngine:
    """Manage model lifecycle"""
    
    def __init__(self, model_registry, trial_period_days: int = 14):
        self.registry = model_registry
        self.trial_period = trial_period_days
    
    async def evaluate_promotion(self, model_id: str) -> dict:
        """Evaluate if model should be promoted"""
        
        model = self.registry.get_model(model_id)
        
        if not model:
            return {"status": "not_found"}
        
        # Collect metrics
        metrics = ModelMetrics(
            backtest_sharpe=model.get('backtest_sharpe', 0),
            backtest_win_rate=model.get('backtest_win_rate', 0),
            backtest_max_dd=model.get('backtest_max_dd', 0),
            walk_forward_sharpe=model.get('walk_forward_sharpe', 0),
            feature_importance_entropy=self._compute_feature_entropy(model),
            trial_sharpe=model.get('trial_sharpe', 0),
            trial_trades=model.get('trial_trades', 0)
        )
        
        eligible, issues = metrics.meets_promotion_criteria()
        
        return {
            "model_id": model_id,
            "eligible": eligible,
            "metrics": {
                "backtest_sharpe": metrics.backtest_sharpe,
                "backtest_win_rate": f"{metrics.backtest_win_rate:.0%}",
                "walk_forward_sharpe": metrics.walk_forward_sharpe,
                "trial_sharpe": metrics.trial_sharpe,
                "trial_trades": metrics.trial_trades
            },
            "issues": issues,
            "recommendation": "PROMOTE" if eligible else "HOLD"
        }
    
    def _compute_feature_entropy(self, model: dict) -> float:
        """Entropy of feature importance (higher = more diverse)"""
        
        importance = model.get('feature_importance', {})
        
        if not importance:
            return 0.0
        
        values = list(importance.values())
        total = sum(values)
        
        # Normalize
        probs = [v / total for v in values]
        
        # Shannon entropy
        entropy = -sum(p * np.log2(p) for p in probs if p > 0)
        
        return entropy
    
    async def promote_model(self, model_id: str) -> dict:
        """Promote model to active"""
        
        eval_result = await self.evaluate_promotion(model_id)
        
        if not eval_result["eligible"]:
            return {
                "status": "ineligible",
                "issues": eval_result["issues"]
            }
        
        # Mark model as promoted
        self.registry.update_model(
            model_id,
            {
                "status": ModelStatus.PROMOTED.value,
                "promoted_at": datetime.now().isoformat(),
                "active": True
            }
        )
        
        return {
            "status": "promoted",
            "model_id": model_id,
            "active_at": datetime.now().isoformat()
        }
    
    async def retire_model(self, model_id: str) -> dict:
        """Retire underperforming model"""
        
        self.registry.update_model(
            model_id,
            {
                "status": ModelStatus.RETIRED.value,
                "retired_at": datetime.now().isoformat(),
                "active": False
            }
        )
        
        return {
            "status": "retired",
            "model_id": model_id
        }
```

## Acceptance Criteria

- [ ] Define promotion thresholds
- [ ] Compute feature importance entropy
- [ ] Evaluate backtest vs walk-forward
- [ ] Run trial period logic
- [ ] Promote eligible models
- [ ] API endpoint for evaluation
- [ ] Audit trail of all promotions
- [ ] Tests pass
