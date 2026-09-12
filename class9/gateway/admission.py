from __future__ import annotations

import urllib.error

from gateway.queue import enqueue
from gateway.metrics import METRICS
from router.router import Router
from gateway.types import Request, Response, Shed, SliceOOM

WINDOW_S = 60.0

class Gateway:

    def __init__(self, router: Router, tokens_per_min: int = 10_000) -> None:
        self.router = router
        self.tokens_per_min = tokens_per_min
        self._window: dict[str, tuple[float, int]] = {}

    def handle(self, req: Request) -> Response:
        METRICS.inc_requests()
        if self._over_cap(req):
            METRICS.inc_shed("tenant_tokens", 429)
            return Shed(
                status=429,
                error="rate_limit_error",
                reason="tenant_tokens",
                message="tenant tokens/min cap",
            ).to_response()

        result = self.router.place(req)
        if isinstance(result, Shed):
            METRICS.inc_shed(result.reason, result.status)
            return result.to_response()
        try:
            hop, completion = enqueue(result, req)
        except SliceOOM:
            return Response(
                status=503,
                error="slice_oom",
                body={"error": {"type": "slice_oom", "message": "gpumem slice exceeded"}},
            )
        except (OSError, TimeoutError, urllib.error.URLError):
            METRICS.inc_shed("no_eligible_pod", 503)
            return Shed(
                status=503,
                error="server_is_overloaded",
                reason="no_eligible_pod",
                message="worker unreachable",
            ).to_response()
        METRICS.inc_completed()
        body: dict = {"id": req.id}
        if hop:
            body["kv_hop"] = hop
        if isinstance(completion, dict):
            for key in ("choices", "model", "usage"):
                if key in completion:
                    body[key] = completion[key]
            if completion.get("id"):
                body["completion_id"] = completion["id"]
        return Response(status=200, handoff=result, body=body)

    def _over_cap(self, req: Request) -> bool:
        cost = int(req.prompt_tokens) + int(req.max_new_tokens)
        start, used = self._window.get(req.tenant, (req.arrival_t, 0))
        if req.arrival_t - start >= WINDOW_S:
            start, used = req.arrival_t, 0
        if used + cost > self.tokens_per_min:
            return True
        self._window[req.tenant] = (start, used + cost)
        return False
