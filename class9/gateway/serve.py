from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from router.overflow import Overflow
from router.router import Router, infer_capability
from gateway.admission import Gateway
from gateway.metrics import METRICS, Metrics
from router.pools import build_pools
from gateway.types import Request

ROOT = Path(__file__).resolve().parents[1]

def build_gateway() -> tuple[Gateway, Metrics]:
    prefill, decode = build_pools()
    return Gateway(Router(prefill, decode)), METRICS

class Handler(BaseHTTPRequestHandler):
    overflow: Overflow
    metrics: Metrics

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/metrics":
            body = self.metrics.render().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/v1/chat/completions":
            self.send_error(404)
            return
        n = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(n)
        payload = json.loads(raw or b"{}")
        req = Request(
            id=str(payload.get("id", "http")),
            arrival_t=0.0,
            priority=int(payload.get("priority", 1)),
            prompt_tokens=int(payload.get("prompt_tokens", 16)),
            max_new_tokens=int(payload.get("max_tokens", payload.get("max_new_tokens", 16))),
            prefix_hash=payload.get("prefix_hash"),
            timeout_s=float(payload.get("timeout_s", 30)),
            tenant=str(payload.get("tenant", "lab")),
            capability=infer_capability(payload),
        )
        resp = self.overflow.send(req)
        body = json.dumps(resp.body).encode("utf-8")
        self.send_response(resp.status)
        self.send_header("Content-Type", "application/json")
        for key, value in resp.headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def main(host: str = "127.0.0.1", port: int = 8080) -> None:
    os.environ.setdefault("TRACE_PATH", str(ROOT / "traces" / "requests.jsonl"))
    gw, metrics = build_gateway()
    Handler.overflow = Overflow(local=gw)
    Handler.metrics = metrics
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"gateway on http://{host}:{port}")
    server.serve_forever()

if __name__ == "__main__":
    main()
