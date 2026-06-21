# Create Setup and Bootstrap Scripts Specification
# Automation for environment, data, and initial config

## setup.sh (Linux/Mac)

```bash
#!/bin/bash
set -e

echo "🚀 Qlib Trading Platform Setup"
echo "================================"

# 1. Check Python
echo "✓ Checking Python 3.11+..."
python3 --version

# 2. Create venv
echo "✓ Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
echo "✓ Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 4. Create directories
echo "✓ Creating directory structure..."
mkdir -p data/qlib
mkdir -p data/market_data
mkdir -p mlruns
mkdir -p logs

# 5. Download Qlib data (US)
echo "✓ Downloading Qlib market data (this may take a while)..."
python -c "
import qlib
qlib.init(provider_uri='data/qlib/qlib_data', region='US')
print('Qlib initialized successfully')
"

# 6. Setup database
echo "✓ Initializing portfolio database..."
python -c "
from src.qlib_research.app.services.portfolio_manager import PortfolioManager
pm = PortfolioManager()
pm.init_db()
print('Database initialized')
"

# 7. Frontend setup
echo "✓ Setting up React frontend..."
cd src/app/frontend
npm install
npm run build
cd ../../..

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the app:"
echo "  1. Backend:  python -m uvicorn src.qlib_research.app.api.main:app --reload"
echo "  2. Frontend: npm run dev (from src/app/frontend)"
echo "  3. Or use:   docker-compose up"
```

## setup.bat (Windows)

```batch
@echo off
setlocal enabledelayedexpansion

echo 🚀 Qlib Trading Platform Setup (Windows)
echo ========================================

REM Check Python
echo ✓ Checking Python 3.11+...
python --version

REM Create venv
echo ✓ Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

REM Install dependencies
echo ✓ Installing Python dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt

REM Create directories
echo ✓ Creating directory structure...
if not exist "data\qlib" mkdir data\qlib
if not exist "data\market_data" mkdir data\market_data
if not exist "mlruns" mkdir mlruns
if not exist "logs" mkdir logs

REM Initialize Qlib
echo ✓ Initializing Qlib...
python -c "import qlib; qlib.init(provider_uri='data/qlib/qlib_data', region='US')"

REM Frontend
echo ✓ Setting up React frontend...
cd src\app\frontend
npm install
npm run build
cd ..\..\..

echo.
echo ✅ Setup complete!
echo.
echo To start the app:
echo   1. Backend:  python -m uvicorn src.qlib_research.app.api.main:app --reload
echo   2. Frontend: npm run dev (from src\app\frontend)
echo   3. Or use:   docker-compose up
```

## Makefile

```makefile
.PHONY: setup install run test clean docker-up docker-down

setup:
	@echo "Running setup..."
	@bash setup.sh

install:
	pip install -r requirements.txt

run:
	docker-compose up

test:
	pytest tests/ -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	docker-compose down -v

docker-up:
	docker-compose up

docker-down:
	docker-compose down
```

## Acceptance Criteria

- [ ] setup.sh works on Linux/Mac
- [ ] setup.bat works on Windows
- [ ] Directories created
- [ ] Qlib initialized
- [ ] Database initialized
- [ ] Frontend built
- [ ] No errors in setup logs
