from __future__ import annotations

from collections import defaultdict

SHED_REASONS = frozenset(
    {"tenant_tokens", "timeout_queue", "kv_free", "p99_spread", "no_eligible_pod"}
)

class Metrics:

    def __init__(self) -> None:
        self.requests_total = 0
        self.shed_total: dict[tuple[str, int], int] = defaultdict(int)
        self.pick_total = 0
        self.pick_unknown_snapshot_total = 0
        self.tokens_in_flight = {"prefill": 0, "decode": 0}
        self.kv_free_ratio = 0.0
        self.planner_desired = {"prefill": 0, "decode": 0}
        self.overflow_total = 0
        self.completed_total = 0
        self.kv_transfer_total = 0
        self.kv_transfer_tokens = 0
        self.kv_evict_total = 0

    def inc_requests(self) -> None:
        self.requests_total += 1

    def inc_shed(self, reason: str, code: int) -> None:
        if reason not in SHED_REASONS:
            reason = "no_eligible_pod"
        self.shed_total[(reason, int(code))] += 1

    def inc_pick(self) -> None:
        self.pick_total += 1

    def inc_unknown_snapshot(self) -> None:
        self.pick_unknown_snapshot_total += 1

    def set_in_flight(self, phase: str, n: int) -> None:
        self.tokens_in_flight[phase] = int(n)

    def set_kv_free(self, ratio: float) -> None:
        self.kv_free_ratio = float(ratio)

    def set_desired(self, pool: str, n: int) -> None:
        self.planner_desired[pool] = int(n)

    def inc_overflow(self) -> None:
        self.overflow_total += 1

    def inc_completed(self) -> None:
        self.completed_total += 1

    def inc_kv_transfer(self, tokens: int) -> None:
        self.kv_transfer_total += 1
        self.kv_transfer_tokens += int(tokens)

    def inc_kv_evict(self, n: int = 1) -> None:
        self.kv_evict_total += int(n)

    def reset(self) -> None:
        self.__init__()
        from router.trace import TRACES

        TRACES.reset()

    def render(self) -> str:
        lines = [
            "# TYPE orch_requests_total counter",
            f"orch_requests_total {self.requests_total}",
            "# TYPE orch_shed_total counter",
        ]
        if not self.shed_total:
            lines.append('orch_shed_total{reason="no_eligible_pod",code="503"} 0')
        for (reason, code), n in sorted(self.shed_total.items()):
            lines.append(f'orch_shed_total{{reason="{reason}",code="{code}"}} {n}')
        lines += [
            "# TYPE orch_pick_total counter",
            f"orch_pick_total {self.pick_total}",
            "# TYPE orch_pick_unknown_snapshot_total counter",
            f"orch_pick_unknown_snapshot_total {self.pick_unknown_snapshot_total}",
            "# TYPE orch_tokens_in_flight gauge",
            f'orch_tokens_in_flight{{phase="prefill"}} {self.tokens_in_flight["prefill"]}',
            f'orch_tokens_in_flight{{phase="decode"}} {self.tokens_in_flight["decode"]}',
            "# TYPE orch_kv_free_ratio gauge",
            f"orch_kv_free_ratio {self.kv_free_ratio}",
            "# TYPE orch_planner_desired_replicas gauge",
            f'orch_planner_desired_replicas{{pool="prefill"}} {self.planner_desired["prefill"]}',
            f'orch_planner_desired_replicas{{pool="decode"}} {self.planner_desired["decode"]}',
            "# TYPE orch_overflow_total counter",
            f"orch_overflow_total {self.overflow_total}",
            "# TYPE orch_completed_total counter",
            f"orch_completed_total {self.completed_total}",
            "# TYPE orch_kv_transfer_total counter",
            f"orch_kv_transfer_total {self.kv_transfer_total}",
            "# TYPE orch_kv_transfer_tokens counter",
            f"orch_kv_transfer_tokens {self.kv_transfer_tokens}",
            "# TYPE orch_kv_evict_total counter",
            f"orch_kv_evict_total {self.kv_evict_total}",
        ]
        return "\n".join(lines) + "\n"

METRICS = Metrics()
