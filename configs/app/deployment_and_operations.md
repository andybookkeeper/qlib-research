# Deployment & Operations Specification
# Docker, docker-compose, configuration management, deployment checklist

## Overview

Deployment provides:
1. **Docker** — Containerized app, backend API, database
2. **Docker Compose** — Local dev/test environment
3. **Environment Config** — Development, testing, production modes
4. **Startup Procedures** — Database init, migrations, cache warmup
5. **Monitoring** — Health checks, restart policies
6. **Backup Strategy** — Daily audit log backups

## Project Structure

```
my-qlib-research/
├── Dockerfile                 # Backend API container
├── docker-compose.yml         # Local dev environment
├── docker-compose.prod.yml    # Production compose (future)
├── .env.example               # Environment template
├── .env                       # Actual env (local)
├── .dockerignore              # Files to skip in Docker build
├── entrypoint.sh              # Container startup script
├── src/
│   ├── qlib_research/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── services/
│   │   │   ├── models/
│   │   │   └── config/
│   │   ├── __main__.py        # Entry point
│   │   └── cli/
│   └── requirements.txt
├── configs/
│   ├── app/                   # All specifications
│   └── deployment/
│       ├── nginx.conf         # Reverse proxy (future)
│       └── systemd/
├── data/
│   ├── qlib/                  # Qlib market data (large)
│   ├── logs/
│   │   ├── app.log
│   │   ├── errors.log
│   │   └── audit.log
│   └── cache/                 # Market data cache
└── tests/
```

## Dockerfile

```dockerfile
# Dockerfile

FROM python:3.10-slim

# Set environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY src/requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY src/ /app/src/
COPY configs/ /app/configs/
COPY data/ /app/data/

# Copy entrypoint
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/monitoring/health || exit 1

# Expose port
EXPOSE 8000

# Run entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
```

## Docker Compose (Development)

```yaml
# docker-compose.yml

version: "3.9"

services:
  # Backend API
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: qlib-api
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - LOG_LEVEL=DEBUG
      - QLIB_DATA_PATH=/app/data/qlib
      - MARKET_DATA_CACHE_TTL_HOURS=1
      - PAPER_TRADING_INITIAL_CASH=100000
    volumes:
      - ./src:/app/src                    # Code hot-reload
      - ./data/qlib:/app/data/qlib        # Qlib data (large)
      - ./data/logs:/app/data/logs        # Log persistence
      - ./configs:/app/configs            # Specs
    depends_on:
      - redis
    networks:
      - qlib-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/monitoring/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s
    restart: unless-stopped

  # Redis cache (optional, for production)
  redis:
    image: redis:7-alpine
    container_name: qlib-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - qlib-network
    restart: unless-stopped

  # Frontend (React/Vue) - optional
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: qlib-frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000/api/v1
    depends_on:
      - api
    networks:
      - qlib-network
    restart: unless-stopped

volumes:
  redis-data:

networks:
  qlib-network:
    driver: bridge
```

## Environment Configuration

```bash
# .env.example

# Application
ENVIRONMENT=development              # development, testing, production
APP_NAME="Qlib Trading Platform"
APP_VERSION="1.0.0"
LOG_LEVEL=INFO

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
SECRET_KEY=your-secret-key-here      # Change in production!

# Database (optional)
DATABASE_URL=sqlite:///./data/qlib_trading.db

# Qlib
QLIB_DATA_PATH=./data/qlib
QLIB_PROVIDER=yahoo                  # yahoo, local, remote
QLIB_AUTO_FETCH=true

# Market Data
MARKET_DATA_CACHE_TTL_HOURS=24
MARKET_DATA_REFRESH_SCHEDULE="0 17 * * *"  # Daily 5pm UTC

# Paper Trading
PAPER_TRADING_INITIAL_CASH=100000
PAPER_TRADING_COMMISSION_PER_TRADE=5.00

# Risk Limits
MAX_POSITION_SIZE_PCT=0.10            # 10% of portfolio
MAX_PORTFOLIO_DELTA=1.5
MAX_DAILY_LOSS_PCT=0.02               # 2% daily loss limit
MAX_DAILY_LOSS_USD=2000
MAX_LEVERAGE=2.0

# Logging
LOG_FILE_PATH=./data/logs/app.log
LOG_FILE_SIZE_MB=10
LOG_BACKUP_COUNT=10
AUDIT_LOG_PATH=./data/logs/audit.log
AUDIT_LOG_BACKUP_COUNT=30

# Deployment
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
DEBUG=false

# Optional: Auth (Phase 2)
AUTH_ENABLED=false
JWT_SECRET=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=1
```

## Entrypoint Script

```bash
#!/bin/bash
# entrypoint.sh

set -e

echo "Starting Qlib Trading Platform..."

# Load environment
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

echo "Environment: $ENVIRONMENT"
echo "Log Level: $LOG_LEVEL"

# Create necessary directories
mkdir -p data/logs
mkdir -p data/cache
mkdir -p data/qlib

# Initialize Qlib data (if needed)
if [ ! -d "data/qlib/stocks" ]; then
    echo "Initializing Qlib data..."
    python -c "from qlib.config import REG; REG.register('default_conf'); import qlib; qlib.init()"
fi

# Health check
echo "Running health check..."
python -m src.qlib_research.app.health_check || echo "Health check skipped (first run)"

# Start FastAPI app
echo "Starting FastAPI server..."
exec python -m uvicorn src.qlib_research.app.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level $LOG_LEVEL \
    --access-log
```

## Startup Procedures

### Pre-Deployment Checklist

```markdown
# Deployment Checklist

## Pre-Deployment
- [ ] All tests passing (unit, integration, e2E)
- [ ] Code reviewed and approved
- [ ] No secrets in .env (checked with git-secrets)
- [ ] Version bumped in setup.py
- [ ] CHANGELOG updated
- [ ] Database migrations created and tested
- [ ] Qlib data downloaded/validated
- [ ] Risk limits reviewed with stakeholders
- [ ] Kill switch tested and ready
- [ ] Backup strategy in place

## Deployment Steps
1. [ ] Build Docker image: `docker build -t qlib-api:1.0.0 .`
2. [ ] Test locally: `docker-compose up`
3. [ ] Run smoke tests
4. [ ] Push to registry (if applicable)
5. [ ] Deploy to staging
6. [ ] Run E2E tests on staging
7. [ ] Get sign-off
8. [ ] Deploy to production
9. [ ] Verify production health
10. [ ] Monitor logs for errors

## Post-Deployment
- [ ] Verify endpoints responsive
- [ ] Check market data fresh
- [ ] Verify audit logging
- [ ] Monitor metrics dashboard
- [ ] Ready to rollback if needed

## Rollback Plan
- [ ] Keep previous image tagged: `qlib-api:0.9.0`
- [ ] Restore backup data if needed
- [ ] Revert config changes
- [ ] Test after rollback
```

## Health Check

```python
# src/qlib_research/app/health_check.py

import sys
from datetime import datetime

def check_qlib():
    """Check Qlib initialization"""
    try:
        import qlib
        from qlib.config import REG
        REG.register('default_conf')
        qlib.init()
        return True, "Qlib OK"
    except Exception as e:
        return False, f"Qlib error: {e}"

def check_market_data():
    """Check market data available"""
    try:
        import os
        qlib_path = os.getenv("QLIB_DATA_PATH", "./data/qlib")
        if os.path.exists(qlib_path):
            return True, "Market data available"
        else:
            return False, "Market data not found"
    except Exception as e:
        return False, f"Market data error: {e}"

def check_dependencies():
    """Check required packages"""
    required = ["fastapi", "pydantic", "numpy", "pandas", "qlib", "lightgbm"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        return False, f"Missing packages: {missing}"
    return True, "All dependencies OK"

def main():
    """Run all health checks"""
    checks = [
        ("Qlib", check_qlib),
        ("Market Data", check_market_data),
        ("Dependencies", check_dependencies)
    ]
    
    all_pass = True
    for name, check_fn in checks:
        ok, msg = check_fn()
        status = "✓" if ok else "✗"
        print(f"{status} {name}: {msg}")
        if not ok:
            all_pass = False
    
    print(f"\nHealth check at {datetime.utcnow().isoformat()}")
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
```

## Backup & Disaster Recovery

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

echo "Backing up audit trail..."
cp data/logs/audit.log $BACKUP_DIR/audit_${TIMESTAMP}.log.gz
gzip $BACKUP_DIR/audit_${TIMESTAMP}.log

# Backup Qlib data (optional, large)
if [ "$BACKUP_QLIB_DATA" = "true" ]; then
    echo "Backing up Qlib data..."
    tar -czf $BACKUP_DIR/qlib_${TIMESTAMP}.tar.gz data/qlib/
fi

# Backup configuration
echo "Backing up configuration..."
cp configs/app/*.md $BACKUP_DIR/configs_${TIMESTAMP}/

# Upload to S3 (future)
# aws s3 cp $BACKUP_DIR s3://qlib-backups/ --recursive

echo "Backup complete: $BACKUP_DIR"

# Cleanup old backups (keep last 30)
find $BACKUP_DIR -type f -mtime +30 -delete
```

## Local Development Setup

```bash
# Setup local development environment

# 1. Clone repository
git clone https://github.com/your-org/my-qlib-research.git
cd my-qlib-research

# 2. Create .env from template
cp .env.example .env

# 3. Build Docker image
docker-compose build

# 4. Start services
docker-compose up

# 5. Verify
curl http://localhost:8000/api/v1/monitoring/health

# 6. View logs
docker-compose logs -f api

# 7. Access frontend
open http://localhost:3000

# To stop
docker-compose down

# To rebuild
docker-compose up --build

# To run tests
docker-compose exec api pytest tests/

# To view audit log
docker-compose exec api tail -f data/logs/audit.log
```

## Production Deployment (Future)

```yaml
# docker-compose.prod.yml (future template)

version: "3.9"

services:
  api:
    image: qlib-api:1.0.0
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    ports:
      - "8000:8000"
    restart: always
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 2G
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./configs/deployment/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - api
    restart: always
```

## Acceptance Criteria

- [ ] Docker build succeeds without errors
- [ ] docker-compose up starts all services
- [ ] Health check endpoint works
- [ ] Logs written to files
- [ ] Market data loads
- [ ] All tests pass in container
- [ ] Environment config works (.env)
- [ ] Backup script runs
- [ ] Deployment checklist followed
- [ ] Rollback tested

## Known Limitations (MVP)

- Single-container deployment (no scaling)
- SQLite only (no production DB)
- No load balancer (nginx future)
- No SSL/TLS (use in dev only)
- Manual backups (no cloud sync)
- No monitoring dashboards
- No auto-scaling
