# Observability & Audit Specification
# Logging, metrics, monitoring, and compliance audit trails

## Overview

Observability provides:
1. **Structured Logging** — All events logged to files and stdout
2. **Metrics** — Performance tracking, latency, error rates
3. **Alerting** — Notifications on errors, risk events
4. **Audit Trail** — Immutable record of all trades and decisions
5. **Dashboards** — Real-time system health (optional Phase 2)

## Logging Strategy

### Log Levels & Events

```python
# src/qlib_research/app/services/logging_service.py

import logging
import json
from datetime import datetime

logger = logging.getLogger("qlib_trading")

class LogEvent:
    """Structured log event"""
    
    # Event types
    TRADE_EXECUTED = "trade_executed"
    TRADE_REJECTED = "trade_rejected"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ERROR_VALIDATION = "error_validation"
    ERROR_RISK_LIMIT = "error_risk_limit"
    SIGNAL_GENERATED = "signal_generated"
    PORTFOLIO_UPDATE = "portfolio_update"
    MARKET_DATA_FETCH = "market_data_fetch"
    SYSTEM_STARTUP = "system_startup"
    
    def __init__(
        self,
        event_type: str,
        level: str = "INFO",
        message: str = "",
        details: dict = None
    ):
        self.timestamp = datetime.utcnow().isoformat()
        self.event_type = event_type
        self.level = level
        self.message = message
        self.details = details or {}
        self.request_id = None  # Set by middleware
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "event": self.event_type,
            "message": self.message,
            "details": self.details,
            "request_id": self.request_id
        }
    
    def log(self):
        """Log to logger"""
        log_method = getattr(logger, self.level.lower())
        log_method(json.dumps(self.to_dict()))

# Usage examples
LogEvent(
    event_type=LogEvent.ORDER_PLACED,
    level="INFO",
    message="Order submitted",
    details={
        "order_id": "ORD_12345",
        "ticker": "AAPL",
        "qty": 100,
        "price": 150.25
    }
).log()

LogEvent(
    event_type=LogEvent.ERROR_RISK_LIMIT,
    level="WARN",
    message="Order rejected: position size limit",
    details={
        "ticker": "NVDA",
        "requested_qty": 1000,
        "max_position_size_pct": 0.10,
        "violation": "would be 15% of portfolio"
    }
).log()
```

### Log File Configuration

```python
# src/qlib_research/app/config/logging_config.py

import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(timestamp)s %(level)s %(name)s %(message)s"
        },
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        },
        "file_info": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "data/logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10
        },
        "file_error": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "json",
            "filename": "data/logs/errors.log",
            "maxBytes": 10485760,
            "backupCount": 10
        },
        "audit_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "data/logs/audit.log",
            "maxBytes": 52428800,  # 50MB for audit trail
            "backupCount": 30  # Keep 30 days
        }
    },
    "loggers": {
        "qlib_trading": {
            "level": "INFO",
            "handlers": ["console", "file_info", "file_error"]
        },
        "qlib_trading.audit": {
            "level": "INFO",
            "handlers": ["audit_file"],
            "propagate": False
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

## Audit Trail

### Trade Audit

```python
# src/qlib_research/app/services/audit_service.py

import logging
from datetime import datetime

audit_logger = logging.getLogger("qlib_trading.audit")

class AuditService:
    """Immutable audit trail of all trades"""
    
    @staticmethod
    def log_trade_execution(
        order_id: str,
        ticker: str,
        side: str,
        quantity: int,
        price: float,
        portfolio_value: float,
        portfolio_pnl: float,
        user_id: str = None
    ):
        """Log executed trade"""
        audit_logger.info(json.dumps({
            "action": "trade_executed",
            "order_id": order_id,
            "timestamp": datetime.utcnow().isoformat(),
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "price": price,
            "cost": quantity * price,
            "portfolio_value": portfolio_value,
            "portfolio_pnl": portfolio_pnl,
            "user_id": user_id or "system"
        }))
    
    @staticmethod
    def log_trade_rejection(
        reason: str,
        ticker: str,
        side: str,
        quantity: int,
        violations: list[str],
        user_id: str = None
    ):
        """Log rejected trade"""
        audit_logger.warning(json.dumps({
            "action": "trade_rejected",
            "timestamp": datetime.utcnow().isoformat(),
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "reason": reason,
            "violations": violations,
            "user_id": user_id or "system"
        }))
    
    @staticmethod
    def log_position_closed(
        ticker: str,
        quantity: int,
        entry_price: float,
        exit_price: float,
        pnl: float,
        pnl_pct: float
    ):
        """Log closed position"""
        audit_logger.info(json.dumps({
            "action": "position_closed",
            "timestamp": datetime.utcnow().isoformat(),
            "ticker": ticker,
            "quantity": quantity,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": pnl,
            "pnl_pct": pnl_pct
        }))
    
    @staticmethod
    def log_risk_limit_change(
        limit_name: str,
        old_value: float,
        new_value: float,
        user_id: str = None
    ):
        """Log risk limit adjustment"""
        audit_logger.info(json.dumps({
            "action": "risk_limit_updated",
            "timestamp": datetime.utcnow().isoformat(),
            "limit": limit_name,
            "old_value": old_value,
            "new_value": new_value,
            "user_id": user_id or "system"
        }))
    
    @staticmethod
    def log_circuit_breaker_triggered(reason: str, halt_value: float = None):
        """Log circuit breaker activation"""
        audit_logger.critical(json.dumps({
            "action": "circuit_breaker_triggered",
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "halt_value": halt_value
        }))
```

## Metrics & Performance Tracking

```python
# src/qlib_research/app/services/metrics_service.py

import time
from collections import defaultdict

class MetricsService:
    """Track performance metrics"""
    
    def __init__(self):
        self.endpoint_latencies = defaultdict(list)  # endpoint -> [latencies]
        self.error_counts = defaultdict(int)         # error_type -> count
        self.trade_counts = defaultdict(int)         # ticker -> count
        self.orders_submitted = 0
        self.orders_filled = 0
        self.orders_rejected = 0
    
    def record_endpoint_latency(self, endpoint: str, latency_ms: float):
        """Record API endpoint latency"""
        self.endpoint_latencies[endpoint].append(latency_ms)
    
    def record_error(self, error_type: str):
        """Record error occurrence"""
        self.error_counts[error_type] += 1
    
    def record_order(self, status: str):
        """Record order outcome"""
        if status == "submitted":
            self.orders_submitted += 1
        elif status == "filled":
            self.orders_filled += 1
        elif status == "rejected":
            self.orders_rejected += 1
    
    def get_metrics_summary(self) -> dict:
        """Get current metrics"""
        import statistics
        
        latency_stats = {}
        for endpoint, latencies in self.endpoint_latencies.items():
            if latencies:
                latency_stats[endpoint] = {
                    "min_ms": min(latencies),
                    "max_ms": max(latencies),
                    "mean_ms": statistics.mean(latencies),
                    "median_ms": statistics.median(latencies),
                    "p95_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else None
                }
        
        return {
            "endpoint_latencies": latency_stats,
            "error_counts": dict(self.error_counts),
            "orders": {
                "submitted": self.orders_submitted,
                "filled": self.orders_filled,
                "rejected": self.orders_rejected,
                "fill_rate": self.orders_filled / max(self.orders_submitted, 1)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
```

## Middleware for Observability

```python
# src/qlib_research/app/api/middleware.py (additions)

import time
import uuid
from fastapi import Request

class ObservabilityMiddleware:
    """Track all requests for observability"""
    
    def __init__(self, app):
        self.app = app
        self.metrics = MetricsService()
    
    async def __call__(self, request: Request, call_next):
        # Generate request ID
        request.state.request_id = str(uuid.uuid4())
        request.state.start_time = time.time()
        
        # Add to logs
        logger.info(f"REQUEST: {request.method} {request.url.path}", extra={
            "request_id": request.state.request_id,
            "method": request.method,
            "path": request.url.path
        })
        
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"ERROR: {str(e)}", extra={
                "request_id": request.state.request_id,
                "error_type": type(e).__name__
            })
            self.metrics.record_error(type(e).__name__)
            raise
        
        # Record latency
        latency = (time.time() - request.state.start_time) * 1000
        self.metrics.record_endpoint_latency(request.url.path, latency)
        
        # Add headers
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Process-Time-Ms"] = f"{latency:.2f}"
        
        logger.info(f"RESPONSE: {request.method} {request.url.path} {response.status_code}", extra={
            "request_id": request.state.request_id,
            "status": response.status_code,
            "latency_ms": latency
        })
        
        return response
```

## API Endpoints for Observability

```python
# src/qlib_research/app/api/routes/monitoring.py

from fastapi import APIRouter

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

@router.get("/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@router.get("/metrics")
async def get_metrics(metrics_service=Depends(get_metrics_service)):
    """Get performance metrics"""
    return metrics_service.get_metrics_summary()

@router.get("/audit-log")
async def get_audit_log(
    days: int = Query(1),
    limit: int = Query(100)
):
    """Get recent audit trail entries"""
    # Read from audit.log file
    entries = []
    with open("data/logs/audit.log", "r") as f:
        for line in f.readlines()[-limit:]:
            entries.append(json.loads(line))
    return {"entries": entries}
```

## Acceptance Criteria

- [ ] All trades logged to audit trail
- [ ] Errors logged with full context
- [ ] Request latency tracked per endpoint
- [ ] Audit trail immutable (append-only)
- [ ] Metrics exposed via /monitoring/metrics
- [ ] Health check endpoint works
- [ ] Logs rotated (10MB per file)
- [ ] JSON format for parsing
- [ ] Request IDs propagated through logs

## Known Limitations (MVP)

- No centralized logging (local files only)
- No real-time dashboards
- No alerting service
- No log aggregation
- Metrics kept in memory (lost on restart)
