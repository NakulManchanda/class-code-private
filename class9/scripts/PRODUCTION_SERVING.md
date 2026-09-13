# From the capacity experiment to production serving

This is a proposed operating design and troubleshooting guide, not a claim that
our lab is production-ready. No deployment is changed by this document.

## Request journey

Client -> HTTPS ingress -> authenticated gateway -> admission and bounded queue
-> capability/model router -> private vLLM service -> response or streaming tokens.
If local admission fails transiently, the gateway may use an approved fallback
provider within the remaining deadline and budget. Observability follows the
same request ID across every hop.

Run the gateway as a managed service near the workers, not on a developer's Mac.
Use private service networking instead of SSH tunnels for production routing.
Keep worker APIs private. Gate readiness on loaded model and inference health;
use graceful draining when replacing workers. Scaling a pod cannot create GPU
capacity that the cluster does not possess.

Authenticate before trusting tenant identity, priority or budget. Validate the
model, modality, request size, output budget and context length. Measure input
tokens server-side using the appropriate tokenizer and reserve output capacity;
reconcile reservations with actual usage and cancellation.

## Failures and decisions

| Signal | Likely meaning / evidence to check | Response and tuning decision |
|---|---|---|
| 400 / context too long | Input plus output exceeds supported context; malformed payload | Correct request, trim with application approval, or use compatible long-context model. Do not retry unchanged. |
| 401 / 403 | Client or provider authentication/authorization failure | Correct secret, scope or policy; do not disguise as capacity failure. |
| 404 / model missing | Served model ID differs from request | Inspect /v1/models and routing config. Do not count error bodies as successful completions. |
| Tenant 429 | Authenticated tenant allowance exhausted | Return retry guidance; bounded client backoff with jitter. Upgrade quota only if justified. Do not bypass quota through fallback. |
| Router 503, kv_free | Routing KV threshold reached | Route to another eligible replica, short bounded queue if deadline allows, or approved fallback. Inspect KV and latency together before adjusting threshold. |
| Router 503, timeout_queue | Queue estimate exceeds remaining service budget | Shed/fallback early; reduce admitted work, add capacity, or offer asynchronous jobs. Increasing timeout alone adds waiting. |
| Router 503, no_eligible_pod | Generic eligibility failure | Inspect ready endpoints, metric reachability/age, model capability and recorded snapshots. It does not establish GPU saturation on its own. |
| GPU OOM / slice_oom | GPU allocation or per-slice limit exceeded | Inspect GPU/process/pod logs; reduce load or rebalance memory. Our lab explicitly does not overflow slice_oom. |
| Connection failure / worker restart | Worker, network or process failure | Remove unhealthy endpoint; retry another worker only within deadline and retry budget. Distinguish network faults from memory pressure. |
| Timeout / 504 | Queue, generation, network or backend exceeded deadline | Locate slow hop, cancel abandoned inference, reserve fallback time. Late fallback can duplicate compute and spend. |
| Backend 429 / 5xx | Provider throttling or outage | Respect retry signals, cap retries, use a circuit breaker. Use another approved backend only if contract and budget allow. |
| 200 but invalid/empty output | Transport succeeded, application contract did not | Validate response schema and required content; trace original worker body. Retry only by explicit policy. |

A circuit breaker temporarily stops calls to a failing dependency, then allows
limited recovery probes. It is different from a quota or a per-request retry.
Use one coordinated retry budget; SDK, gateway and client retries can otherwise
multiply. Never silently switch providers after emitting part of a streamed
answer: clients would receive two unrelated generations. Define whether to
terminate the stream or offer an explicit restart.

## Choosing parameters by workload

First define latency and quality goals: time to first token (TTFT), time between
tokens, completion deadline, output quality and acceptable cost per request.
Then benchmark representative prompt lengths, output lengths and arrival rates.
Our 64-concurrent experiment is a load input, not a production capacity promise.

| Control | Choose using | Main tradeoff |
|---|---|---|
| Output max_tokens | Product response-length needs and remaining context | More tokens retain resources longer. The lab's 32-token fallback cap is not equivalent to a 1,024-token answer. |
| max_model_len | Required input + output context | Reject or reroute larger requests; do not raise past model/hardware support. |
| Gateway concurrency / queue bound | Measured latency under representative load | More admitted requests can increase queueing without increasing useful throughput. |
| Tenant tokens/min | Fairness, authenticated customer tier and available capacity | A quota controls fairness, not worker health; maintain it across replicas. |
| KV routing threshold | Latency, preemption and burst headroom | Lower routes away sooner and costs more; higher may tolerate more local pressure. Our 80% is lab policy, not universal best practice. |
| Resume threshold / hysteresis | Observed routing oscillations | Separate stop/resume boundaries avoid flapping. Proposed example: stop above 80%, resume below 65%; validate, do not deploy blindly. |
| Deadline / timeout | End-to-end latency goal | Budget queue + local inference + optional fallback inside client deadline; do not give each hop a fresh full timeout. |
| Fallback budget | Spending limit and provider rate limit | Production needs shared time-window/token/cost limits, not a process-lifetime request counter. |
| Minimum replicas / scale trigger | Normal demand, burst size, measured startup time | Warm capacity costs money; reactive scaling may arrive after a short burst has ended. |

For interactive chat, prioritize bounded waiting and predictable streaming;
for offline batch, allow longer queues and optimize throughput; for long-context
work, consider a separate pool so a few expensive sequences do not dominate
short requests. Restrict fallback to models/providers that meet modality, tool,
structured-output, privacy and quality requirements. Changing models is a
product choice, not merely an HTTP routing choice.

vLLM tuning: reducing max_num_seqs or max_num_batched_tokens can reduce memory
pressure. With chunked prefill, smaller token batches can favor inter-token
latency while larger batches can favor prompt processing. Benchmark the tradeoff
on the installed version rather than copying defaults. See the official
[optimization guide](https://docs.vllm.ai/en/latest/configuration/optimization/).

gpu_memory_utilization is a per-instance memory fraction, not the gateway's KV
occupancy threshold. On shared GPUs budget all instances and runtime headroom;
do not independently assign most GPU memory to both workers. See the official
[configuration reference](https://docs.vllm.ai/en/latest/api/vllm/config/).

ignore_eos=true is our stress-test setting; ordinary user-facing generation
should normally honor model stop conditions.

## Troubleshooting order

1. Identify the exact path: direct worker, local Python runner, or deployed HTTP
   gateway. A passing test on one path does not prove the others.
2. Correlate request ID, final status, original local status, reason and worker.
   A final 200 may be local or fallback; a 503 is not proof of provider usage.
3. Check /v1/models and validate a short real completion, including its body.
4. Inspect running/waiting sequences, KV usage, latency percentiles and errors.
   vLLM exposes running, waiting and KV-cache metrics; metric names are
   version-dependent. See [production metrics](https://docs.vllm.ai/en/latest/usage/metrics/).
5. Check pods, endpoints, restarts, worker logs and GPU allocation for actual
   failures. Capture the snapshot used in a decision, not just a later sample.
6. Change one control at a time; rerun representative traffic and compare good
   completions, latency, output quality and cost. Preserve rollback settings.

From the Mac, the existing make commands reproduce the lab paths:

```bash
make port-forward  # only if tunnels are not already running; keep this terminal open
# Another Mac terminal:
make test-429
make test-503
make test-saturation LAB_REQUESTS=256 LAB_CONCURRENCY=64
make test-overflow LAB_REQUESTS=256 LAB_CONCURRENCY=64 LAB_OVERFLOW_LIMIT=20
make superlinked-usage
```

For remote inspection, run make ssh on the Mac, then these inside Lambda:

```bash
kubectl get pods -o wide
kubectl get svc,endpoints
kubectl logs deploy/orch-serve --tail=100
kubectl logs deploy/vllm-prefill --tail=100
```

These are diagnostics, not a production deployment command. Protect logs and
traces: the lab trace can contain generated text; avoid unnecessary prompt,
response or credential logging in production.

## Gaps in this repository before production

- gateway/serve.py is a demonstration HTTP handler. It does not propagate prompt
  or messages into Request, sets arrival_t=0, accepts client tenant/accounting
  fields, and lacks production authentication, validation and streaming.
- The fixed arrival timestamp means the HTTP path's rate-limit time window does
  not advance correctly. Its per-process accounting also is not a shared,
  atomic multi-replica quota.
- router/pools.py's ordinary VLLMWorker still caps output at 128 and can swallow
  worker 4xx bodies. Our new LoadWorker guards its own path; that did not fix
  the deployed worker adapter.
- Worker-error mapping can conflate failures with overload; preserve original
  status/reason and do not turn client errors into retryable capacity failures.
- Overflow uses a process-local lifetime cap. The lab adds serialization for
  cap enforcement; production needs a shared budget and bounded concurrency.
- The 500 path retries locally once and directly returns that result. It does
  not rerun all fallback classification on that retry result.
- Metrics are fetched during routing; under load, repeated polling and changing
  snapshots can affect decisions and reason labels. Use a controlled collection
  cadence, freshness limits and decision snapshot logging.
- The deployed orch-serve pod lacked Superlinked configuration when inspected.
  Store provider credentials in managed secrets and verify deployed integration.
- Startup installs, rollout/draining, cancellation, retry budgeting, streaming,
  observability and load qualification need a production design and tests.

Our successful experiment proves the real worker-capacity-to-fallback path in
the runner. It does not remove these production gaps.
