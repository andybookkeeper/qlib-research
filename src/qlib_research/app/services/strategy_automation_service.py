"""Feature-flagged strategy automation proposal workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4


@dataclass
class StrategyProposal:
    proposal_id: str
    user_id: int
    ticker: str
    side: str
    quantity: float
    confidence: float
    rationale: str
    suggested_price: Optional[float] = None
    status: str = "proposed"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    executed_order_id: Optional[str] = None
    executed_at: Optional[str] = None


class StrategyAutomationService:
    """Create and track strategy-generated trade proposals."""

    def __init__(self) -> None:
        self._proposals: Dict[str, StrategyProposal] = {}

    def create_proposal(
        self,
        *,
        user_id: int,
        ticker: str,
        side: str,
        quantity: float,
        confidence: float,
        rationale: str,
        suggested_price: Optional[float] = None,
    ) -> Dict[str, object]:
        proposal = StrategyProposal(
            proposal_id=f"sp-{uuid4().hex[:12]}",
            user_id=user_id,
            ticker=ticker.upper(),
            side=side.lower(),
            quantity=float(quantity),
            confidence=float(confidence),
            rationale=rationale.strip() or "No rationale provided.",
            suggested_price=suggested_price,
        )
        self._proposals[proposal.proposal_id] = proposal
        return asdict(proposal)

    def get_proposal(self, proposal_id: str, user_id: int) -> Optional[Dict[str, object]]:
        proposal = self._proposals.get(proposal_id)
        if proposal is None or proposal.user_id != user_id:
            return None
        return asdict(proposal)

    def mark_executed(self, proposal_id: str, user_id: int, order_id: str) -> Optional[Dict[str, object]]:
        proposal = self._proposals.get(proposal_id)
        if proposal is None or proposal.user_id != user_id:
            return None
        proposal.status = "executed"
        proposal.executed_order_id = str(order_id)
        proposal.executed_at = datetime.utcnow().isoformat()
        return asdict(proposal)

    def list_proposals(self, user_id: int, limit: int = 50) -> Dict[str, object]:
        proposals = [asdict(p) for p in self._proposals.values() if p.user_id == user_id]
        proposals.sort(key=lambda item: item["created_at"], reverse=True)
        return {"count": len(proposals[:limit]), "proposals": proposals[:limit]}
