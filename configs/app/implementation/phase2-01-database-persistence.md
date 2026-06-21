# Phase 2-01: Database Persistence (PostgreSQL Migration)

**Status**: Implementation  
**Duration**: 2 weeks (Weeks 1-2 of Phase 2)  
**Priority**: CRITICAL (foundation for all Phase 2 features)  
**Team**: Copilot + User

---

## 🎯 Objective

Migrate from **in-memory singletons** (Phase 1 MVP) to **PostgreSQL with SQLAlchemy ORM**, providing:
- ✅ Durable data storage
- ✅ Multi-user portfolio isolation
- ✅ Transaction management
- ✅ Schema versioning (Alembic)
- ✅ Query optimization (indexes, relationships)
- ✅ Connection pooling

---

## 📊 Current State (Phase 1)

### What We Have
```python
# Phase 1: In-memory singletons (NOT durable)
PortfolioTracker()  # Global singleton, lost on restart
RiskValidator()     # Global singleton, lost on restart
positions = {}      # Dict in memory
orders = {}         # Dict in memory
```

### Problems with Phase 1 Approach
- ❌ Data lost on restart
- ❌ Not multi-user capable
- ❌ No transaction safety
- ❌ No audit trail
- ❌ No schema versioning
- ❌ Can't scale to production

---

## 🏗️ PostgreSQL Schema Design

### Core Tables (8 tables)

#### 1. **users** - User accounts
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. **portfolios** - User portfolios
```sql
CREATE TABLE portfolios (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    initial_capital DECIMAL(15, 2) NOT NULL,
    current_cash DECIMAL(15, 2) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, name)
);
CREATE INDEX idx_portfolios_user_id ON portfolios(user_id);
```

#### 3. **positions** - Current holdings
```sql
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price DECIMAL(15, 4) NOT NULL,
    current_price DECIMAL(15, 4) NOT NULL,
    entry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(portfolio_id, symbol)
);
CREATE INDEX idx_positions_portfolio_id ON positions(portfolio_id);
```

#### 4. **orders** - Order records
```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- BUY, SELL
    quantity INTEGER NOT NULL,
    order_price DECIMAL(15, 4),  -- NULL for MARKET
    fill_price DECIMAL(15, 4),   -- NULL if not filled
    order_type VARCHAR(20) NOT NULL,  -- MARKET, LIMIT, STOP
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- PENDING, FILLED, CANCELLED, REJECTED
    stop_price DECIMAL(15, 4),  -- For STOP orders
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filled_at TIMESTAMP,
    rejected_reason TEXT,
    UNIQUE(portfolio_id, id)
);
CREATE INDEX idx_orders_portfolio_id ON orders(portfolio_id);
CREATE INDEX idx_orders_status ON orders(status);
```

#### 5. **trades** - Executed trades
```sql
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    execution_price DECIMAL(15, 4) NOT NULL,
    commission DECIMAL(15, 4) NOT NULL,
    gross_pnl DECIMAL(15, 2),  -- For close trades
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_trades_portfolio_id ON trades(portfolio_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
```

#### 6. **risk_limits** - User-configured limits
```sql
CREATE TABLE risk_limits (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    limit_type VARCHAR(50) NOT NULL,  -- VAR_95, VAR_99, SHARPE_MIN, MAX_LEVERAGE, etc
    limit_value DECIMAL(15, 4) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(portfolio_id, limit_type)
);
CREATE INDEX idx_risk_limits_portfolio_id ON risk_limits(portfolio_id);
```

#### 7. **alerts** - Risk/system alerts
```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL,  -- RISK_LIMIT_BREACH, ORDER_REJECTED, etc
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'INFO',  -- INFO, WARNING, ERROR
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP
);
CREATE INDEX idx_alerts_portfolio_id ON alerts(portfolio_id);
CREATE INDEX idx_alerts_acknowledged ON alerts(acknowledged);
```

#### 8. **audit_log** - Compliance/audit trail
```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    portfolio_id INTEGER REFERENCES portfolios(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,  -- ORDER_CREATED, ORDER_EXECUTED, etc
    entity_type VARCHAR(50),
    entity_id INTEGER,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
```

---

## 🔧 Implementation Steps

### Step 1: PostgreSQL Setup (1-2 hours)

#### 1a. Install & Configure PostgreSQL
```bash
# On Windows (using WSL or Docker recommended)
docker run --name qlib-postgres \
  -e POSTGRES_USER=qlib_user \
  -e POSTGRES_PASSWORD=qlib_password \
  -e POSTGRES_DB=qlib_trading \
  -p 5432:5432 \
  -v qlib_postgres_data:/var/lib/postgresql/data \
  postgres:15
```

#### 1b. Create Connection String
```python
# .env file
DATABASE_URL=postgresql://qlib_user:qlib_password@localhost:5432/qlib_trading
```

#### 1c. Verify Connection
```bash
pip install psycopg2-binary
python -c "from sqlalchemy import create_engine; engine = create_engine('postgresql://...'); engine.connect()"
```

---

### Step 2: SQLAlchemy ORM Models (2-3 hours)

Create `src/qlib_research/app/models/database.py`:

```python
from sqlalchemy import Column, Integer, String, Decimal, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")

class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    initial_capital = Column(Decimal(15, 2), nullable=False)
    current_cash = Column(Decimal(15, 2), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="portfolio", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="portfolio", cascade="all, delete-orphan")
    risk_limits = relationship("RiskLimit", back_populates="portfolio", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="portfolio", cascade="all, delete-orphan")

class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Decimal(15, 4), nullable=False)
    current_price = Column(Decimal(15, 4), nullable=False)
    entry_date = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    portfolio = relationship("Portfolio", back_populates="positions")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Integer, nullable=False)
    order_price = Column(Decimal(15, 4))
    fill_price = Column(Decimal(15, 4))
    order_type = Column(String(20), nullable=False)
    status = Column(String(20), default='PENDING')
    stop_price = Column(Decimal(15, 4))
    created_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime)
    rejected_reason = Column(Text)
    
    portfolio = relationship("Portfolio", back_populates="orders")
    trades = relationship("Trade", back_populates="order")

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    execution_price = Column(Decimal(15, 4), nullable=False)
    commission = Column(Decimal(15, 4), nullable=False)
    gross_pnl = Column(Decimal(15, 2))
    executed_at = Column(DateTime, default=datetime.utcnow)
    
    order = relationship("Order", back_populates="trades")
    portfolio = relationship("Portfolio", back_populates="trades")

class RiskLimit(Base):
    __tablename__ = "risk_limits"
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    limit_type = Column(String(50), nullable=False)
    limit_value = Column(Decimal(15, 4), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    portfolio = relationship("Portfolio", back_populates="risk_limits")

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), default='INFO')
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime)
    
    portfolio = relationship("Portfolio", back_populates="alerts")
```

---

### Step 3: Alembic Migration System (1-2 hours)

```bash
pip install alembic

# Initialize Alembic
alembic init migrations

# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

---

### Step 4: Database Session Management (1 hour)

Create `src/qlib_research/app/db/session.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://qlib_user:qlib_password@localhost/qlib_trading")

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # No connection pooling for simplicity (add later)
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """Dependency injection for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### Step 5: Refactor Broker Service (3-4 hours)

Migrate `src/qlib_research/app/services/broker_service.py` to use ORM:

```python
# Old (Phase 1): In-memory singletons
class PortfolioTracker:
    def add_trade(self, symbol: str, side: str, quantity: int, price: float):
        # In-memory update
        pass

# New (Phase 2): ORM with persistence
class PortfolioTracker:
    def __init__(self, db: Session):
        self.db = db
    
    def add_trade(self, portfolio_id: int, symbol: str, side: str, quantity: int, price: float):
        # Create Order + Trade records
        order = Order(portfolio_id=portfolio_id, symbol=symbol, side=side, quantity=quantity, ...)
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order
```

---

### Step 6: Update API Routes (3-4 hours)

Refactor routes to use database sessions:

```python
@router.post("/orders")
def create_order(
    order_request: OrderRequest,
    db: Session = Depends(get_db)
):
    # Query from database
    portfolio = db.query(Portfolio).filter_by(id=order_request.portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404)
    
    # Create order
    order = Order(**order_request.dict())
    db.add(order)
    db.commit()
    db.refresh(order)
    return order
```

---

### Step 7: Data Migration (2-3 hours)

Export Phase 1 data, import to Phase 2:

```python
# Migration script
def migrate_phase1_to_phase2(db: Session):
    # Load Phase 1 SQLite data
    # Insert into Phase 2 PostgreSQL
    # Verify data integrity
    pass
```

---

### Step 8: Testing & Verification (2-3 hours)

```bash
# Run existing tests with PostgreSQL
pytest tests/unit/ -v

# New test cases
pytest tests/integration/test_database.py -v

# Verify data persistence
# Restart app, check data is still there
```

---

## 📋 Task Breakdown

| Task | Owner | Est. Hours | Status |
|------|-------|-----------|--------|
| PostgreSQL setup | Copilot | 2 | 📋 Ready |
| ORM models | Copilot | 3 | 📋 Ready |
| Alembic setup | Copilot | 2 | 📋 Ready |
| Session management | Copilot | 1 | 📋 Ready |
| Broker service refactor | Copilot | 4 | 📋 Ready |
| API routes refactor | Copilot | 4 | 📋 Ready |
| Data migration | Copilot | 3 | 📋 Ready |
| Testing & verification | Copilot | 3 | 📋 Ready |
| **TOTAL** | | **22 hours** | |

---

## 🎯 Success Criteria

✅ Phase 2-01 is complete when:

- [ ] PostgreSQL is running and accessible
- [ ] All 8 tables created with indexes
- [ ] SQLAlchemy ORM models work correctly
- [ ] Alembic migrations are tested
- [ ] Broker service works with ORM
- [ ] All 15 existing API endpoints still work
- [ ] All unit tests pass (81+)
- [ ] Phase 1 data successfully migrated
- [ ] No data loss during migration
- [ ] Performance is acceptable (<200ms queries)

---

## 📊 Expected Outcomes

### Before (Phase 1)
```
Data Storage: In-memory dicts
Persistence: ❌ Lost on restart
Multi-user: ❌ No isolation
Transactions: ❌ None
Audit Trail: ❌ None
Queries: ❌ Linear search
```

### After (Phase 2)
```
Data Storage: PostgreSQL 15+
Persistence: ✅ ACID compliant
Multi-user: ✅ Row-level isolation
Transactions: ✅ Full support
Audit Trail: ✅ Complete audit_log
Queries: ✅ Indexed, <50ms
```

---

## ⚠️ Potential Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| PostgreSQL connection failures | Connection pooling, retry logic, fallback |
| Data migration corruption | Backup before migration, verify row counts |
| Performance degradation | Indexes on all foreign keys, query optimization |
| ORM query N+1 problem | Eager loading with `joinedload` |
| SQLAlchemy Session conflicts | Use dependency injection consistently |

---

## 🚀 Next Steps (After Phase 2-01 Complete)

1. **Phase 2-02**: WebSocket real-time updates
2. **Phase 2-03**: User authentication & JWT
3. **Phase 2-04**: Multi-user portfolios
4. **Phase 2-05**: Risk limit enforcement

---

## 📞 Quick Reference

### Key Files to Create/Modify
- `src/qlib_research/app/models/database.py` - ORM models (NEW)
- `src/qlib_research/app/db/session.py` - Session management (NEW)
- `src/qlib_research/app/services/broker_service.py` - Refactor for ORM
- `src/qlib_research/app/api/routes/*.py` - Update endpoints
- `migrations/` - Alembic migration directory (NEW)
- `.env` - Database connection string (NEW)
- `requirements.txt` - Add sqlalchemy, alembic, psycopg2

### Key Dependencies
```
sqlalchemy==2.0.20
alembic==1.12.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
```

---

**Status**: Ready to implement  
**Start Date**: Now  
**Estimated Completion**: 2-3 days (depending on parallel work)

---

*Phase 2-01 Implementation Plan Created: 2026-06-20*
