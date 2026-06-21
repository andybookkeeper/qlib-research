"""Broker abstraction layer for Phase 3 adapter-based routing."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Protocol

from sqlalchemy.orm import Session

from src.qlib_research.app.services.broker_service import DatabaseBrokerService

logger = logging.getLogger("qlib_trading.broker_adapter")


class BrokerAdapter(Protocol):
    """Broker adapter contract used by API routes."""

    def create_order(
        self,
        ticker: str,
        side: str,
        quantity: float,
        order_type: str,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        current_price: Optional[float] = None,
        user_id: Optional[int] = None,
    ): ...

    def get_orders(self, user_id: Optional[int] = None, limit: int = 100): ...

    def get_order(self, order_id: int, user_id: Optional[int] = None): ...

    def fill_order(self, order_id: int, current_price: float, user_id: Optional[int] = None): ...

    def get_positions(self, user_id: Optional[int] = None): ...

    def get_position(self, symbol: str, user_id: Optional[int] = None): ...

    def get_trades(self, user_id: Optional[int] = None): ...

    def get_portfolio_snapshot(self, current_prices: Optional[Dict[str, float]] = None, user_id: Optional[int] = None): ...

    def reset(self, user_id: Optional[int] = None): ...

    def get_connection_status(self) -> Dict[str, object]: ...

    def get_account_snapshot(self, user_id: Optional[int] = None) -> Dict[str, object]: ...

    def sync_account_snapshot(self, user_id: Optional[int] = None) -> Dict[str, object]: ...


class PaperBrokerAdapter:
    """Default adapter backed by existing database broker service."""

    def __init__(self, db: Session):
        self._service = DatabaseBrokerService(db)

    def create_order(
        self,
        ticker: str,
        side: str,
        quantity: float,
        order_type: str,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        current_price: Optional[float] = None,
        user_id: Optional[int] = None,
    ):
        return self._service.create_order(
            ticker=ticker,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            current_price=current_price,
            user_id=user_id,
        )

    def get_orders(self, user_id: Optional[int] = None, limit: int = 100):
        return self._service.get_orders(user_id=user_id, limit=limit)

    def get_order(self, order_id: int, user_id: Optional[int] = None):
        return self._service.get_order(order_id=order_id, user_id=user_id)

    def fill_order(self, order_id: int, current_price: float, user_id: Optional[int] = None):
        return self._service.fill_order(order_id=order_id, current_price=current_price, user_id=user_id)

    def get_positions(self, user_id: Optional[int] = None):
        return self._service.get_positions(user_id=user_id)

    def get_position(self, symbol: str, user_id: Optional[int] = None):
        return self._service.get_position(symbol=symbol, user_id=user_id)

    def get_trades(self, user_id: Optional[int] = None):
        return self._service.get_trades(user_id=user_id)

    def get_portfolio_snapshot(self, current_prices: Optional[Dict[str, float]] = None, user_id: Optional[int] = None):
        return self._service.get_portfolio_snapshot(current_prices=current_prices, user_id=user_id)

    def reset(self, user_id: Optional[int] = None):
        return self._service.reset(user_id=user_id)

    def get_connection_status(self) -> Dict[str, object]:
        return {
            "adapter_mode": "paper",
            "connected": True,
            "read_only": False,
            "execution_enabled": False,
            "message": "Paper broker adapter active",
        }

    def get_account_snapshot(self, user_id: Optional[int] = None) -> Dict[str, object]:
        snapshot = self._service.get_portfolio_snapshot(user_id=user_id)
        return {
            "source": "paper",
            "synced_at": datetime.utcnow().isoformat(),
            "portfolio_value": snapshot["portfolio_value"],
            "cash": snapshot["current_cash"],
            "open_positions": snapshot["open_positions"],
            "total_trades": snapshot["total_trades"],
        }

    def sync_account_snapshot(self, user_id: Optional[int] = None) -> Dict[str, object]:
        return self.get_account_snapshot(user_id=user_id)


class LiveBrokerSkeletonAdapter(PaperBrokerAdapter):
    """Phase 3 live-broker skeleton in read-only mode with paper fallback execution."""

    def __init__(self, db: Session):
        super().__init__(db)
        self._provider = os.getenv("PHASE3_LIVE_BROKER_PROVIDER", "not-configured").strip()

    def get_connection_status(self) -> Dict[str, object]:
        return {
            "adapter_mode": "live_skeleton",
            "connected": False,
            "read_only": True,
            "execution_enabled": False,
            "provider": self._provider,
            "message": "Live broker skeleton adapter is in read-only mode with paper execution fallback.",
        }

    def get_account_snapshot(self, user_id: Optional[int] = None) -> Dict[str, object]:
        snapshot = super().get_account_snapshot(user_id=user_id)
        snapshot["source"] = "live_skeleton"
        snapshot["provider"] = self._provider
        snapshot["read_only"] = True
        return snapshot

    def sync_account_snapshot(self, user_id: Optional[int] = None) -> Dict[str, object]:
        snapshot = self.get_account_snapshot(user_id=user_id)
        snapshot["sync_mode"] = "local-paper-fallback"
        return snapshot


def create_broker_adapter(db: Session, enable_live_broker_adapter: bool) -> BrokerAdapter:
    """Resolve broker adapter. Live path is read-only skeleton with paper fallback."""
    if enable_live_broker_adapter:
        logger.info("[BROKER] Using live broker skeleton adapter (read-only + paper fallback).")
        return LiveBrokerSkeletonAdapter(db)
    return PaperBrokerAdapter(db)
