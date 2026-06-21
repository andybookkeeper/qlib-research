"""WebSocket real-time update endpoints."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Dict, Set

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from src.qlib_research.app.api.dependencies import get_current_active_user
from src.qlib_research.app.db import get_db
from src.qlib_research.app.models.database import User
from src.qlib_research.app.services.auth_service import decode_access_token
from src.qlib_research.app.services.realtime_service import realtime_hub

router = APIRouter()


def _normalize_tickers(values) -> Set[str]:
    if not values:
        return set()
    if isinstance(values, str):
        return {ticker.strip().upper() for ticker in values.split(",") if ticker.strip()}
    if isinstance(values, list):
        return {str(ticker).strip().upper() for ticker in values if str(ticker).strip()}
    return set()


@router.websocket("/ws")
async def realtime_stream(websocket: WebSocket):
    """Websocket endpoint for price, order, and portfolio events."""
    token = websocket.query_params.get("token")
    username = decode_access_token(token) if token else None
    if not username:
        await websocket.close(code=1008)
        return

    db: Session = next(get_db())
    try:
        user = db.query(User).filter(User.username == username).first()
    finally:
        db.close()
    if user is None or not user.is_active:
        await websocket.close(code=1008)
        return

    client_id = websocket.query_params.get("client_id") or str(uuid.uuid4())[:8]
    initial_tickers = _normalize_tickers(websocket.query_params.get("tickers"))

    await realtime_hub.connect(
        websocket,
        client_id=client_id,
        tickers=initial_tickers,
        user_id=user.id,
    )
    await websocket.send_json(
        {
            "event": "connected",
            "data": {
                "client_id": client_id,
                "user_id": user.id,
                "subscriptions": sorted(list(initial_tickers)),
            },
        }
    )

    try:
        while True:
            try:
                raw_message = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                message = json.loads(raw_message)
            except asyncio.TimeoutError:
                await websocket.send_json({"event": "heartbeat", "data": realtime_hub.status()})
                continue
            except json.JSONDecodeError:
                await websocket.send_json({"event": "error", "data": {"message": "Invalid JSON payload"}})
                continue

            action = str(message.get("action", "")).lower()
            tickers = _normalize_tickers(message.get("tickers"))

            if action == "subscribe":
                subscriptions = realtime_hub.subscribe(client_id, tickers)
                await websocket.send_json(
                    {"event": "subscribed", "data": {"subscriptions": sorted(list(subscriptions))}}
                )
            elif action == "unsubscribe":
                subscriptions = realtime_hub.unsubscribe(client_id, tickers)
                await websocket.send_json(
                    {"event": "unsubscribed", "data": {"subscriptions": sorted(list(subscriptions))}}
                )
            elif action == "ping":
                await websocket.send_json({"event": "pong", "data": realtime_hub.status()})
            elif action == "status":
                await websocket.send_json({"event": "status", "data": realtime_hub.status()})
            else:
                await websocket.send_json(
                    {
                        "event": "error",
                        "data": {
                            "message": "Unsupported action",
                            "supported_actions": ["subscribe", "unsubscribe", "ping", "status"],
                        },
                    }
                )
    except WebSocketDisconnect:
        realtime_hub.disconnect(client_id)
    except Exception:
        realtime_hub.disconnect(client_id)
        raise


@router.get("/status")
async def realtime_status(current_user: User = Depends(get_current_active_user)) -> Dict:
    """Returns active websocket clients and subscriptions."""
    status = realtime_hub.status()
    filtered_clients = []
    for client_id in status.get("clients", []):
        owner = status.get("owners", {}).get(client_id)
        if owner == current_user.id:
            filtered_clients.append(client_id)
    return {
        "active_clients": len(filtered_clients),
        "clients": filtered_clients,
        "subscriptions": {
            cid: status.get("subscriptions", {}).get(cid, [])
            for cid in filtered_clients
        },
    }
