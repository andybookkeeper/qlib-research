# src/qlib_research/app/api/main.py
"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.qlib_research.app.api.routes import market, features, training, broker, risk, portfolio, research

logger = logging.getLogger("qlib_trading.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown events."""
    
    # Startup
    logger.info("🚀 Starting Qlib Trading API")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Qlib Trading API")


# Create FastAPI app
app = FastAPI(
    title="Qlib Trading Platform API",
    description="Quantitative trading with Qlib research engine",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routes
@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "app": "Qlib Trading Platform",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "ready"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "qlib_trading_api",
        "version": "0.1.0"
    }


@app.get("/api/status")
async def api_status():
    """Detailed API status."""
    return {
        "api": "operational",
        "components": {
            "qlib": "initializing",
            "broker": "ready",
            "database": "ready"
        }
    }


# Include routers
app.include_router(market.router, prefix="/api/market", tags=["market"])
app.include_router(features.router, prefix="/api/features", tags=["features"])
app.include_router(training.router, prefix="/api/training", tags=["training"])
app.include_router(broker.router, prefix="/api/broker", tags=["broker"])
app.include_router(risk.router, prefix="/api/risk", tags=["risk"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(research.router, prefix="/api/research", tags=["research"])


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.qlib_research.app.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
