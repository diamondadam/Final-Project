from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

import httpx


@dataclass
class WorkOrderPayload:
    segment_id: int
    severity: str                    # "DEGRADED" or "DAMAGED"
    belief: list[float]              # [P(Healthy), P(Degraded), P(Damaged)]
    confidence: float                # max(belief)
    commanded_speed_fps: float
    alert_message: str

    def to_dict(self) -> dict:
        return {
            "source": "rail-digital-twin",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **asdict(self),
        }


@dataclass
class WorkOrder:
    id: str
    segment_id: int
    severity: str                    # "DEGRADED" | "DAMAGED"
    belief: list[float]
    confidence: float
    commanded_speed_fps: float
    alert_message: str
    created_at: str
    status: str = "OPEN"             # "OPEN" | "COMPLETED"
    completed_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class WorkOrderStore:
    """In-memory store for local work order tracking."""

    def __init__(self) -> None:
        self._orders: dict[str, WorkOrder] = {}

    def find_open(self, segment_id: int) -> WorkOrder | None:
        """Return the open work order for a segment, if one exists."""
        for wo in self._orders.values():
            if wo.segment_id == segment_id and wo.status == "OPEN":
                return wo
        return None

    def add_or_escalate(self, payload: WorkOrderPayload) -> WorkOrder:
        """Create a new work order, or escalate an existing open one for the same segment."""
        existing = self.find_open(payload.segment_id)
        if existing is not None:
            existing.severity = payload.severity
            existing.belief = list(payload.belief)
            existing.confidence = payload.confidence
            existing.commanded_speed_fps = payload.commanded_speed_fps
            existing.alert_message = payload.alert_message
            return existing
        return self.add(payload)

    def add(self, payload: WorkOrderPayload) -> WorkOrder:
        wo = WorkOrder(
            id=str(uuid.uuid4()),
            segment_id=payload.segment_id,
            severity=payload.severity,
            belief=list(payload.belief),
            confidence=payload.confidence,
            commanded_speed_fps=payload.commanded_speed_fps,
            alert_message=payload.alert_message,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._orders[wo.id] = wo
        return wo

    def complete(self, order_id: str) -> WorkOrder | None:
        wo = self._orders.get(order_id)
        if wo is None or wo.status == "COMPLETED":
            return None
        wo.status = "COMPLETED"
        wo.completed_at = datetime.now(timezone.utc).isoformat()
        return wo

    def get(self, order_id: str) -> WorkOrder | None:
        return self._orders.get(order_id)

    def list_all(self) -> list[WorkOrder]:
        return sorted(self._orders.values(), key=lambda w: w.created_at, reverse=True)


class WorkOrderClient:
    """
    Async HTTP client that POSTs work orders to the external maintenance API.

    Configuration via environment variables (never hardcode credentials):
        WORK_ORDER_API_URL  — base URL, e.g. https://maintenance.example.com/api/v1
        WORK_ORDER_API_KEY  — bearer token
        WORK_ORDER_TIMEOUT_S — request timeout in seconds (default 5.0)

    If WORK_ORDER_API_URL is unset, from_env() returns None and the orchestrator
    skips work order submission silently — safe for local dev.

    Failure handling: one retry on transient error (5xx / network timeout).
    Persistent failures are logged and swallowed — never raised into the OODA loop.
    """

    _ENDPOINT = "/work-orders"

    def __init__(self, base_url: str, api_key: str, timeout_s: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._timeout = timeout_s

    @classmethod
    def from_env(cls) -> "WorkOrderClient | None":
        """
        Build a client from environment variables.
        Returns None if WORK_ORDER_API_URL is unset (disables integration).
        """
        url = os.getenv("WORK_ORDER_API_URL")
        if not url:
            return None
        key = os.getenv("WORK_ORDER_API_KEY", "")
        timeout = float(os.getenv("WORK_ORDER_TIMEOUT_S", "5.0"))
        return cls(base_url=url, api_key=key, timeout_s=timeout)

    async def submit(self, payload: WorkOrderPayload) -> None:
        """
        POST a work order. Retries once on transient failure.
        Logs and returns on persistent failure — never raises.
        """
        url = self._base_url + self._ENDPOINT
        body = payload.to_dict()

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in (1, 2):
                try:
                    resp = await client.post(url, json=body, headers=self._headers)
                    if resp.status_code < 500:
                        # 2xx = success, 4xx = caller error (don't retry)
                        if resp.status_code >= 400:
                            print(
                                f"  [WARN] Work order rejected ({resp.status_code}) "
                                f"for seg {payload.segment_id}: {resp.text[:200]}"
                            )
                        return
                    # 5xx — retry once
                    if attempt == 2:
                        print(
                            f"  [WARN] Work order server error ({resp.status_code}) "
                            f"for seg {payload.segment_id} after 2 attempts."
                        )
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    if attempt == 2:
                        print(
                            f"  [WARN] Work order network failure for "
                            f"seg {payload.segment_id}: {exc}"
                        )
