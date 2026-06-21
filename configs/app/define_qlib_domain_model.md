# Define Qlib Domain Model Specification
# Core concepts: Instruments, Factors, Models, Predictions

## Data Model

```python
# src/qlib_research/models/domain.py

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class AssetType(str, Enum):
    STOCK = "stock"
    OPTION = "option"
    FUTURE = "future"

@dataclass
class Instrument:
    """Financial instrument"""
    symbol: str
    name: str
    asset_type: AssetType
    exchange: str
    active: bool = True

@dataclass
class FactorDefinition:
    """Factor/feature definition"""
    name: str
    description: str
    formula: str  # e.g., "close - open"
    data_source: str  # "qlib", "yahoo", "custom"
    refresh_frequency: str  # "daily", "hourly"

@dataclass
class Model:
    """Trained ML model"""
    model_id: str
    name: str
    model_type: str  # "LightGBM", "XGBoost"
    features: list[str]
    training_period: str
    backtest_sharpe: float
    win_rate: float
    max_drawdown: float
    promoted: bool
    created_at: datetime

@dataclass
class Signal:
    """Signal from model"""
    model_id: str
    instrument: Instrument
    action: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0.0-1.0
    expected_return: float
    generated_at: datetime

@dataclass
class Trade:
    """Executed trade"""
    trade_id: str
    instrument: Instrument
    side: str  # "BUY", "SELL"
    quantity: int
    entry_price: float
    entry_time: datetime
    exit_price: float = None
    exit_time: datetime = None
    pnl: float = 0.0
    pnl_pct: float = 0.0

@dataclass
class Portfolio:
    """Current holdings"""
    positions: list[tuple[Instrument, int]]  # (instrument, quantity)
    cash_balance: float
    total_market_value: float
    realized_pnl: float
    unrealized_pnl: float
```

## Qlib Setup

```python
# src/qlib_research/qlib_init.py

import qlib
from qlib.constant import REG_US
from pathlib import Path

def initialize_qlib(
    data_path: str = "data/qlib/cn_data",
    region: str = "US"
):
    """Initialize Qlib provider"""
    
    # Region config
    if region.upper() == "US":
        config = {
            "qlib_dir": data_path,
            "region": "US",
            "provider_uri": f"{data_path}/qlib_data",
            "provider": {
                "class": "LocalProvider",
                "module_path": "qlib.data.provider"
            }
        }
    else:
        config = {
            "qlib_dir": data_path,
            "region": "CN",
            "provider_uri": f"{data_path}/qlib_data"
        }
    
    qlib.init(**config)
    
    return qlib

# Usage
qlib = initialize_qlib(region="US")
```

## Acceptance Criteria

- [ ] Domain models defined
- [ ] Qlib initialization working
- [ ] Data model maps to Qlib concepts
- [ ] Type hints complete
- [ ] Docstrings added
