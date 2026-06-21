"""Background scheduler for broker reconciliation runs."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Optional

from src.qlib_research.app.config import get_phase3_feature_flags
from src.qlib_research.app.db import SessionLocal
from src.qlib_research.app.models.database import User
from src.qlib_research.app.services.broker_adapter import create_broker_adapter
from src.qlib_research.app.services.broker_reconciliation_service import BrokerReconciliationService
from src.qlib_research.app.services.realtime_service import realtime_hub

logger = logging.getLogger("qlib_trading.reconciliation_scheduler")


class ReconciliationScheduler:
    """Run periodic reconciliation and publish user alerts."""

    def __init__(self, service: Optional[BrokerReconciliationService] = None) -> None:
        self._service = service or BrokerReconciliationService()
        self._interval_seconds = int(os.getenv("PHASE3_RECONCILIATION_INTERVAL_SECONDS", "900"))
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_run_at: Optional[str] = None
        self._last_run_summary: Optional[Dict[str, object]] = None

    async def _run_once(self) -> Dict[str, object]:
        flags = get_phase3_feature_flags()
        if not flags["enable_broker_reconciliation"]:
            return {
                "status": "skipped",
                "reason": "feature_disabled",
                "processed_users": 0,
                "alerts_emitted": 0,
            }

        processed_users = 0
        alerts_emitted = 0
        db = SessionLocal()
        try:
            users = db.query(User).filter(User.is_active == True).all()
            broker = create_broker_adapter(db=db, enable_live_broker_adapter=flags["enable_live_broker_adapter"])
            for user in users:
                processed_users += 1
                result = self._service.reconcile(broker=broker, user_id=user.id)
                alerts = result.get("alerts", [])
                if alerts:
                    alerts_emitted += 1
                    await realtime_hub.broadcast(
                        event_type="reconciliation_alert",
                        data={
                            "status": result.get("status"),
                            "is_aligned": result.get("is_aligned"),
                            "alerts": alerts,
                            "reconciled_at": result.get("reconciled_at"),
                        },
                        user_id=user.id,
                    )
        finally:
            db.close()

        return {
            "status": "ok",
            "processed_users": processed_users,
            "alerts_emitted": alerts_emitted,
        }

    async def _run_loop(self) -> None:
        while self._running:
            try:
                summary = await self._run_once()
                self._last_run_at = datetime.utcnow().isoformat()
                self._last_run_summary = summary
            except Exception as exc:
                logger.error("Reconciliation scheduler loop failed: %s", exc, exc_info=True)
                self._last_run_summary = {"status": "error", "error": str(exc)}
            await asyncio.sleep(max(self._interval_seconds, 60))

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def status(self) -> Dict[str, object]:
        return {
            "running": self._running,
            "interval_seconds": self._interval_seconds,
            "last_run_at": self._last_run_at,
            "last_run_summary": self._last_run_summary,
        }
