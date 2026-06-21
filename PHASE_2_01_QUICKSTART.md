# Phase 2-01 Quick Start Guide

## 📦 What You Get

✅ 14 database tables with full ORM support  
✅ Time-series price & feature data  
✅ Multi-user portfolio management  
✅ Audit logging & compliance tracking  
✅ FastAPI + SQLAlchemy integration  

---

## 🔧 Quick Setup

### 1. Database is Auto-Initialized
```bash
uvicorn src.qlib_research.app.api.main:app
# Database tables created automatically on startup
```

### 2. Use in FastAPI Routes
```python
from fastapi import Depends
from src.qlib_research.app.db import get_db
from src.qlib_research.app.models import Portfolio

@app.get("/portfolios/")
def get_portfolios(db = Depends(get_db)):
    return db.query(Portfolio).all()
```

### 3. Use Outside FastAPI
```python
from src.qlib_research.app.db import get_db_sync
from src.qlib_research.app.models import User

db = get_db_sync()
try:
    user = db.query(User).filter_by(username="john").first()
finally:
    db.close()
```

---

## 📊 Available Models

```python
from src.qlib_research.app.models import (
    User,              # User accounts
    Portfolio,         # Trading accounts  
    Position,          # Current holdings
    Order,             # Order records
    Trade,             # Trade history
    PriceHistory,      # Time-series prices (OHLCV)
    FeatureData,       # Time-series indicators
    BacktestResult,    # Strategy backtests
    PortfolioSnapshot, # Daily portfolio state
    RiskLimit,         # Risk constraints
    Alert,             # System alerts
    AuditLog,          # Compliance trail
)
```

---

## ⚙️ Configuration

### Default (SQLite)
```
Database: ./data/qlib_trading.db
No additional setup needed
```

### PostgreSQL
```bash
# Edit .env or set environment variable
export DATABASE_URL="postgresql://user:password@localhost:5432/qlib_trading"

# App will auto-create tables on first run
```

---

## 🧪 Verify Database

```python
from src.qlib_research.app.db import verify_connection
if verify_connection():
    print("Database is ready!")
```

---

## 🚀 Next Phase Options

**Phase 2-02**: WebSocket real-time updates  
**Phase 2-03**: User authentication & JWT  
**Phase 2-04**: Refactor broker service to use DB  

Choose based on priority!

---

**Ready to build?** Start with Phase 2-02, 2-03, or 2-04! 🎯
