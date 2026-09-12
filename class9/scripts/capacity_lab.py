"""Capacity experiments using the real router and real vLLM worker metrics."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import threading
import time
import uuid

from dotenv import load_dotenv
from gateway.admission import Gateway
from gateway.types import Request, request_messages
from router.overflow import Overflow
from router.pools import VLLMWorker
from router.router import Router
from router.trace import TRACES


class LoadWorker(VLLMWorker):
    """Lab-only adapter: sustained generation rather than the normal 128-token cap."""
    def enqueue(self, req, phase='both'):
        data = json.loads(self._post('/v1/chat/completions', {
            'model': self.model,
            'messages': request_messages(req),
            'max_tokens': req.max_new_tokens,
            'ignore_eos': True,
        }))
        if not isinstance(data, dict) or data.get('error') or 'choices' not in data:
            raise ValueError(f'Worker rejected request: {data}')
        return data


class BoundedOverflow(Overflow):
    # The base counter is not atomic. Serialize fallback to enforce the spend cap.
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lock = threading.Lock()

    def _overflow(self, *args, **kwargs):
        with self.lock:
            return super()._overflow(*args, **kwargs)


def reached_target(mode, events):
    if mode == '429':
        return any(e['status'] == 429 and e['via'] == 'local' for e in events)
    if mode == '503':
        return any(e['status'] == 503 and e['via'] == 'local' for e in events)
    return any(e.get('reason') == 'kv_free' and (
        (mode == 'saturation' and e['status'] == 503 and e['via'] == 'local') or
        (mode == 'overflow' and e['status'] == 200 and e['via'] == 'overflow'
         and e.get('local_status') == 503)
    ) for e in events)


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['429', '503', 'saturation', 'overflow'])
    parser.add_argument('--concurrency', type=int, default=32)
    parser.add_argument('--requests', type=int, default=128)
    parser.add_argument('--tokens', type=int, default=1024)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--overflow-limit', type=int, default=3)
    args = parser.parse_args()
    if min(args.concurrency, args.requests, args.tokens, args.timeout) <= 0 or args.overflow_limit < 1:
        parser.error('counts, timeout, tokens and overflow limit must be positive')
    os.environ['LAB_SPLIT'] = 'capability'
    os.environ['OVERFLOW_MAX_REQS'] = str(args.overflow_limit if args.mode == 'overflow' else 0)
    os.environ['OVERFLOW_MAX_TOKENS'] = '32'
    if args.mode == 'overflow' and not all(os.getenv(k) for k in (
        'OVERFLOW_BASE_URL', 'OVERFLOW_MODEL', 'OVERFLOW_API_KEY'
    )):
        parser.error('Set OVERFLOW_BASE_URL, OVERFLOW_MODEL and OVERFLOW_API_KEY in .env')
    run = uuid.uuid4().hex[:10]
    trace = Path('traces') / f'capacity-{args.mode}-{run}.jsonl'
    os.environ['TRACE_PATH'] = str(trace)
    TRACES.reset()
    workers = []
    if args.mode in ('saturation', 'overflow'):
        urls = os.getenv('PREFILL_URLS', 'http://127.0.0.1:8000').split(',')
        for i, url in enumerate(urls):
            worker = LoadWorker(str(i), url.strip(), timeout_s=args.timeout,
                                model=os.getenv('TEXT_MODEL', os.getenv('LOCAL_MODEL', 'lab')))
            models = json.loads(worker._get('/v1/models'))['data']
            ids = [m['id'] for m in models]
            if worker.model not in ids:
                if len(ids) != 1:
                    parser.error(f'Set TEXT_MODEL to one of {ids}')
                print(f'Configured model {worker.model} unavailable; using served model {ids[0]}')
                worker.model = ids[0]
            model_info = next(m for m in models if m['id'] == worker.model)
            context_limit = model_info.get('max_model_len')
            if context_limit and args.tokens + 128 > context_limit:
                parser.error(f'Output budget needs prompt headroom within context limit {context_limit}')
            print(f'Served model: {worker.model}; context limit: {context_limit}')
            snap = worker.snapshot()
            if not snap.healthy or snap.kv_free_ratio is None:
                parser.error(f'{url}: worker unreachable or KV metric missing. Start make port-forward.')
            print(f'Worker {url}: KV usage={1-snap.kv_free_ratio:.1%}, running={snap.running}, waiting={snap.waiting}')
            workers.append(worker)
    # Unique tenant per load request prevents tenant policy masking fleet capacity.
    gateway = Gateway(Router(workers, workers), tokens_per_min=10000 if args.mode == '429' else 10**9)
    flow = BoundedOverflow(local=gateway)
    count = args.requests if workers else 1
    print(f'Mode={args.mode}, requests={count}, concurrency={args.concurrency}, tokens={args.tokens}')
    print('429/503 modes are deterministic policy checks; saturation/overflow use real worker KV metrics.')
    started = time.monotonic()
    errors = []

    def send(i):
        req = Request(f'{run}-{i}', time.monotonic(), 1, 64,
                      10001 if args.mode == '429' else args.tokens, None,
                      args.timeout, f'{run}-{i}', prompt=(
                          f'Experiment {run} request {i}. Write a detailed numbered tutorial about GPU inference, '
                          'with many examples and explanations. Continue until the output budget is exhausted.'
                      ))
        try:
            response = flow.send(req)
            print(f'[{i}] status={response.status} via={response.via} local_status={response.local_status}', flush=True)
        except Exception as exc:
            errors.append(type(exc).__name__)
            print(f'[{i}] ERROR {type(exc).__name__}: {exc}', flush=True)

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        list(pool.map(send, range(count)))
    events = TRACES.events
    print(f'Wall time: {time.monotonic()-started:.2f}s; attempted: {count}; exceptions: {len(errors)}')
    print('Outcomes:', dict(Counter((e['status'], e['via'], e.get('reason')) for e in events)))
    print(f'Trace: {trace}')
    passed = reached_target(args.mode, events)
    print('TARGET OBSERVED' if passed else 'TARGET NOT OBSERVED — inspect traces; increase load only if workers remain healthy.')
    return 0 if passed and not errors else 1


if __name__ == '__main__':
    raise SystemExit(main())
