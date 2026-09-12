from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

STALE_S = 5.0

KV_SATURATION = 0.80

STICKY_OVERLAP = 0.8
STICKY_TAU = 10_000

PLAN_HIGH_WATER = 0.7

@dataclass
class Request:
    id: str
    arrival_t: float
    priority: int
    prompt_tokens: int
    max_new_tokens: int
    prefix_hash: str | None
    timeout_s: float
    tenant: str
    aborted: bool = False

    capability: str = "text"
    prompt: str = ""
    messages: list | None = None

def request_messages(req: Request) -> list:
    if req.messages:
        return req.messages
    return [{"role": "user", "content": req.prompt or req.id}]

@dataclass
class Snapshot:
    pod_id: str
    age_s: float
    healthy: bool = True
    saturating: bool = False
    kv_free_ratio: float | None = None
    tokens_in_flight: int | None = None
    uncached_prefill_tokens: int | None = None
    active_requests: int | None = None
    queue_depth: int | None = None
    waiting: int | None = None
    running: int | None = None
    prefix_tokens: dict[str, int] | None = None

    soak_weight: float = 1.0

@dataclass
class Shed:

    status: int
    error: str
    reason: str = "no_eligible_pod"
    retry_after_s: float | None = None
    message: str = ""

    def to_response(self) -> Response:
        headers: dict[str, str] = {}
        if self.status in (503, 529):
            headers["Retry-After"] = str(int(self.retry_after_s or 2))
        return Response(
            status=self.status,
            error=self.error,
            reason=self.reason,
            headers=headers,
            body={"error": {"type": self.error, "message": self.message}},
        )

@dataclass
class Handoff:
    prefill: Worker
    decode: Worker

@dataclass
class Response:
    status: int
    error: str | None = None
    reason: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    body: dict = field(default_factory=dict)
    handoff: Handoff | None = None

    via: str = "local"
    local_status: int | None = None

class SliceOOM(Exception):
    pass


class Worker(Protocol):
    id: str

    def enqueue(self, req: Request, phase: str = "both") -> dict | None: ...
    def snapshot(self) -> Snapshot: ...
    def abort(self, req_id: str) -> None: ...
