"""WebSocket connection hub for real-time market and broker updates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional, Set

from fastapi import WebSocket


class RealtimeHub:
    """Manages active websocket clients and topic subscriptions."""

    def __init__(self) -> None:
        self._clients: Dict[str, WebSocket] = {}
        self._subscriptions: Dict[str, Set[str]] = {}
        self._owners: Dict[str, int] = {}

    async def connect(
        self,
        websocket: WebSocket,
        client_id: str,
        tickers: Optional[Set[str]] = None,
        user_id: Optional[int] = None,
    ) -> None:
        """Accept websocket and register client."""
        await websocket.accept()
        self._clients[client_id] = websocket
        self._subscriptions[client_id] = set(tickers or set())
        if user_id is not None:
            self._owners[client_id] = int(user_id)

    def disconnect(self, client_id: str) -> None:
        """Remove disconnected client."""
        self._clients.pop(client_id, None)
        self._subscriptions.pop(client_id, None)
        self._owners.pop(client_id, None)

    def subscribe(self, client_id: str, tickers: Set[str]) -> Set[str]:
        """Subscribe client to symbols."""
        if client_id not in self._subscriptions:
            self._subscriptions[client_id] = set()
        self._subscriptions[client_id].update(tickers)
        return self._subscriptions[client_id]

    def unsubscribe(self, client_id: str, tickers: Set[str]) -> Set[str]:
        """Unsubscribe client from symbols."""
        if client_id not in self._subscriptions:
            self._subscriptions[client_id] = set()
        self._subscriptions[client_id].difference_update(tickers)
        return self._subscriptions[client_id]

    async def _send_to_client(self, client_id: str, payload: Dict) -> bool:
        websocket = self._clients.get(client_id)
        if websocket is None:
            return False

        try:
            await websocket.send_json(payload)
            return True
        except Exception:
            self.disconnect(client_id)
            return False

    async def broadcast(
        self,
        event_type: str,
        data: Dict,
        ticker: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> int:
        """Broadcast event to clients, optionally filtered by symbol subscription."""
        payload = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        delivered = 0
        client_ids = list(self._clients.keys())
        for client_id in client_ids:
            subscriptions = self._subscriptions.get(client_id, set())
            owner = self._owners.get(client_id)
            if user_id is not None and owner != user_id:
                continue
            if ticker and subscriptions and ticker not in subscriptions:
                continue
            sent = await self._send_to_client(client_id, payload)
            if sent:
                delivered += 1
        return delivered

    async def broadcast_price_update(
        self,
        ticker: str,
        price: float,
        volume: int,
        change_pct: float,
        user_id: Optional[int] = None,
    ) -> int:
        """Broadcast standardized price update event."""
        return await self.broadcast(
            event_type="price_update",
            data={
                "ticker": ticker,
                "price": price,
                "volume": volume,
                "change_pct": change_pct,
            },
            ticker=ticker,
            user_id=user_id,
        )

    def status(self) -> Dict:
        """Return connection and subscription counts."""
        return {
            "active_clients": len(self._clients),
            "clients": sorted(self._clients.keys()),
            "subscriptions": {
                client_id: sorted(list(symbols))
                for client_id, symbols in self._subscriptions.items()
            },
            "owners": self._owners.copy(),
        }


realtime_hub = RealtimeHub()
