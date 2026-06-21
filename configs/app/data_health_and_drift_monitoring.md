# Data Health and Drift Monitoring Specification
# Detect market data quality issues and model input drift

## Overview

Monitor data freshness, completeness, and statistical drift:
1. **Data validation** — Check for NaN, gaps, outliers
2. **Drift detection** — Compare live vs training distribution
3. **Alerts** — Flag stale or corrupted data
4. **Remediation** — Fallback, skip signals, or trigger retrain

## Implementation

```python
# src/qlib_research/app/services/data_health_monitor.py

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging
import numpy as np

logger = logging.getLogger("qlib_trading.data_health")

class DataQualityLevel(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"

@dataclass
class HealthMetrics:
    """Data quality metrics"""
    freshness_hours: float      # How old is latest data
    completeness_pct: float     # % of expected tickers with data
    null_pct: float             # % null values
    outlier_pct: float          # % values >3 std from mean
    drift_score: float          # 0.0-1.0 (1.0 = high drift)
    status: DataQualityLevel

class DataHealthMonitor:
    """Monitor data quality"""
    
    def __init__(
        self,
        market_data_service,
        backtest_stats: dict = None,
        max_age_hours: int = 24,
        max_drift: float = 0.3
    ):
        self.market_data = market_data_service
        self.backtest_stats = backtest_stats or {}  # Mean, std per ticker
        self.max_age_hours = max_age_hours
        self.max_drift = max_drift
    
    async def check_health(self) -> HealthMetrics:
        """Run health check"""
        
        logger.info("Checking data health...")
        
        try:
            # Get latest market data
            data = await self.market_data.get_latest_ohlcv()
            
            # Check freshness
            freshness = self._check_freshness(data)
            
            # Check completeness
            completeness = self._check_completeness(data)
            
            # Check null/outliers
            null_pct, outlier_pct = self._check_data_quality(data)
            
            # Check drift
            drift = self._check_drift(data)
            
            # Determine status
            status = self._determine_status(
                freshness, completeness, null_pct, outlier_pct, drift
            )
            
            metrics = HealthMetrics(
                freshness_hours=freshness,
                completeness_pct=completeness,
                null_pct=null_pct,
                outlier_pct=outlier_pct,
                drift_score=drift,
                status=status
            )
            
            logger.info(f"Data health: {status.value} (drift: {drift:.2f})")
            return metrics
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return HealthMetrics(
                freshness_hours=999,
                completeness_pct=0,
                null_pct=1.0,
                outlier_pct=0,
                drift_score=1.0,
                status=DataQualityLevel.CRITICAL
            )
    
    def _check_freshness(self, data: dict) -> float:
        """How old is the data"""
        
        timestamps = [d.get('timestamp') for d in data.values()]
        latest = max(timestamps)
        
        age = datetime.now() - latest
        hours = age.total_seconds() / 3600
        
        return hours
    
    def _check_completeness(self, data: dict) -> float:
        """% of expected tickers with data"""
        
        # Assume 500 stocks in universe
        expected_count = 500
        actual_count = len(data)
        
        return (actual_count / expected_count) * 100
    
    def _check_data_quality(self, data: dict) -> tuple:
        """Check nulls and outliers"""
        
        null_count = 0
        outlier_count = 0
        total_points = 0
        
        for ticker, ohlcv in data.items():
            close = ohlcv.get('close')
            volume = ohlcv.get('volume')
            
            if close is None or volume is None:
                null_count += 1
            
            total_points += 1
            
            # Check for outliers (>3 sigma from training)
            if ticker in self.backtest_stats:
                mean = self.backtest_stats[ticker].get('close_mean', 0)
                std = self.backtest_stats[ticker].get('close_std', 1)
                
                if abs(close - mean) > 3 * std:
                    outlier_count += 1
        
        null_pct = null_count / max(total_points, 1)
        outlier_pct = outlier_count / max(total_points, 1)
        
        return null_pct, outlier_pct
    
    def _check_drift(self, data: dict) -> float:
        """Measure input distribution drift"""
        
        if not self.backtest_stats:
            return 0.0  # No baseline
        
        total_drift = 0.0
        count = 0
        
        for ticker, ohlcv in data.items():
            if ticker not in self.backtest_stats:
                continue
            
            close = ohlcv.get('close', 0)
            
            stats = self.backtest_stats[ticker]
            train_mean = stats.get('close_mean', 0)
            train_std = stats.get('close_std', 1)
            
            # Z-score
            z_score = abs((close - train_mean) / max(train_std, 1))
            
            # Drift = how many stddevs away (normalized to 0-1)
            drift = min(z_score / 5, 1.0)  # Cap at 5 sigma = 100% drift
            
            total_drift += drift
            count += 1
        
        avg_drift = total_drift / max(count, 1)
        
        return avg_drift
    
    def _determine_status(
        self,
        freshness: float,
        completeness: float,
        null_pct: float,
        outlier_pct: float,
        drift: float
    ) -> DataQualityLevel:
        """Determine overall status"""
        
        # Critical if data too old
        if freshness > self.max_age_hours:
            return DataQualityLevel.CRITICAL
        
        # Critical if too much missing
        if completeness < 70:
            return DataQualityLevel.CRITICAL
        
        # Critical if too many nulls
        if null_pct > 0.1:
            return DataQualityLevel.CRITICAL
        
        # Critical if high drift
        if drift > self.max_drift:
            return DataQualityLevel.CRITICAL
        
        # Degraded if warnings
        if freshness > self.max_age_hours * 0.5:
            return DataQualityLevel.DEGRADED
        
        if null_pct > 0.01:
            return DataQualityLevel.DEGRADED
        
        if outlier_pct > 0.05:
            return DataQualityLevel.DEGRADED
        
        return DataQualityLevel.HEALTHY
```

## Acceptance Criteria

- [ ] Check data freshness (timestamp)
- [ ] Check completeness (% tickers with data)
- [ ] Detect nulls and outliers
- [ ] Measure input distribution drift
- [ ] Classify as healthy/degraded/critical
- [ ] Alert on critical status
- [ ] API endpoint
- [ ] Scheduled checks (hourly)
- [ ] Tests pass
