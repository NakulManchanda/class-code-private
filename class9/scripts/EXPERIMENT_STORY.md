# The day our local capacity spilled into Superlinked

## Scene 1: The requests arrived on the Mac

We ran:

```bash
make test-overflow LAB_REQUESTS=256 LAB_CONCURRENCY=64 LAB_OVERFLOW_LIMIT=20
```

The capacity runner created 256 requests, with up to 64 executing concurrently.
The rest waited in the Mac's thread-pool work queue. This client-side waiting
is distinct from the vLLM scheduler's queue on Lambda.

The gateway and router for this experiment were Python objects in the Mac's
runner process. We did not send requests through the deployed orch-serve HTTP
server on Lambda. The already-running SSH tunnels connected our local runner
to the real remote workers.

Earlier, the old traffic script went directly to the worker. Those tests could
exercise inference, but could not exercise our gateway's fallback policy.
We also caught a test-adapter bug: requests named a model the worker did not
serve, and error bodies were being reported as successful responses. The runner
now discovers the served model and rejects those error bodies.

## Scene 2: The gateway checked the ticket

Each request first entered Gateway.handle. Admission control checked the
accounted prompt-plus-output token budget against the tenant allowance.

Our deterministic make test-429 deliberately exceeded a 10,000-token allowance.
That produced 429, via=local. A tenant-policy rejection does not invoke fallback.
It is not evidence that GPU memory is full, and this code does not automatically
queue or retry that rejected request.

For the real capacity experiment, the runner gave requests separate tenants and
a large allowance so tenant policy would not hide the fleet-capacity boundary.
The prompt-token count here is a lab accounting estimate, not server tokenization.

## Scene 3: The router looked into the worker

The router chose the text pool and retrieved worker /metrics snapshots. It
checked health, freshness and KV-cache availability, then applied its selection
logic. The worker on forwarded port 8000 advertised Qwen/Qwen3-0.6B with a
2,048-token context limit at the time of these experiments.

Our active route was:

Mac Make target -> capacity_lab.py -> Gateway -> Router -> LoadWorker
-> SSH tunnel -> Lambda vLLM HTTP API -> scheduler -> GPU inference.

The worker's metric responses traveled back through the tunnel to the router.
The single selected text worker performed both prompt prefill and token decode.
Despite service names such as prefill/decode, this capability-mode text run did
not split those phases across two workers.

## Scene 4: The little KV boxes filled

Think of model weights as the machinery already installed in GPU memory.
KV-cache blocks are the changing working space for sequences using that machinery.
Weights and KV cache are different allocations; 80% KV usage is not 80% of all
GPU memory.

During prefill, the transformer processes prompt tokens and creates key and
value tensors at its attention layers. During decode, each new token attends to
previous state and adds its own key/value state. Keeping those tensors avoids
recomputing all earlier keys and values at every generation step.

A sequence's logical token blocks map to physical KV-cache blocks. More active
sequences and longer retained contexts require more cache space. The diagram's
boxes illustrate those blocks, not literal measured block counts or a captured
occupancy timeline. Block sizes, layer counts, head geometry and KV data type
were not measured in this experiment.

The load-only adapter requested 1,024 output tokens and used ignore_eos=true to
keep generation running rather than ending at an early EOS token. It bypassed
the regular adapter's 128-output-token cap. Requests still had to fit the model's
context limit. Successful completion releases blocks for reuse; prefix caching
can retain reusable state, so cache behavior is not simply a universal reset to
zero after each response.

## Scene 5: We reached the boundary

At 128 requests and 32 concurrent, all 128 completed locally in 29.57 seconds.
That run did not observe the target saturation condition.

At 256 requests and 64 concurrent, with fallback disabled, we observed:

- 203 local successes.
- 29 local 503s with reason=kv_free.
- 24 local 503s with reason=no_eligible_pod.

The kv_free results were the important evidence. The router's policy excludes
workers when observed KV usage exceeds 80%. With no eligible worker left, it
sheds the request with 503. This is a routing capacity boundary, not proof that
vLLM crashed, physically exhausted every memory block, or independently returned
503 because it was full.

The no_eligible_pod label is less specific. It does not by itself establish the
underlying cause. Metrics change during requests, and the router can take more
than one snapshot while selecting workers and reporting a shed reason. We have
not attributed those outcomes to a particular failure mode.

Our deterministic make test-503 separately used an empty worker pool. It proved
the no-worker policy path, not real saturation.

## Scene 6: The overflow wrapper called the backup

The local 503 returned to the Overflow wrapper, still running on the Mac.
When the fallback allowance remained, the wrapper called the configured
Superlinked API over HTTPS with the configured credentials and model.

It sent a fresh prompt for inference. It did not transfer Lambda's KV cache or
resume Lambda's partially generated sequence. The Superlinked output budget was
capped at 32 tokens, rather than the 1,024-token local load budget; successful
fallback here proves availability, not equivalent output length.

A successful fallback returned status=200, via=overflow, local_status=503.
Those fields mean: local admission/routing could not serve this request, but the
backup answered successfully. A final 503 alone is not successful overflow.
The wrapper also supports fallback for 529; tenant 429 and slice-OOM responses
are deliberately excluded by its policy.

The lab wrapper serializes fallback calls to enforce its per-run allowance.
Therefore fallback latency and the allowance also influence experiment timing.

## Scene 7: The final tally

With a 20-call fallback allowance, the observed 256-request run finished in
37.51 seconds of actual wall time:

- 235 completed locally.
- 5 completed through Superlinked after kv_free.
- 15 completed through Superlinked after no_eligible_pod.
- 1 returned a local 503 after the fallback allowance was consumed.

That is 255 successful responses out of 256, including 20 successful fallback
calls. Five explicitly demonstrated the desired story: measured local KV
pressure -> router 503 -> Superlinked success.

The evidence file for that run is:
traces/capacity-overflow-ad7d23d553.jsonl

The traces are local experiment output and are ignored by Git. They include
routing decisions, status, reason, timings and returned model/usage details.
The console screenshot supplied in the conversation was from a prior run and
must not be treated as a billing measurement for this run.

## The other boxes in the deployment

The Lambda Kubernetes deployment also contained an orch-serve gateway pod,
a second vLLM service and Mooncake. At inspection, orch-serve had no Superlinked
environment configuration; our successful test used the Mac's .env instead.
The second worker is available to the capability-routing setup, but these text
requests did not demonstrate its vision path. Mooncake was deployed, but these
runs did not demonstrate inter-worker KV transfer or distributed cache reuse.
Planner/KEDA material exists in the lab; these results do not demonstrate an
autoscaling event.

We proved the local runner's real capacity-to-fallback path against Lambda.
We did not prove every path in the wider deployed architecture.

## Replay from the Mac

Keep the existing worker tunnels running; do not open duplicate tunnels:

```bash
make port-forward
```

In another terminal in ~/dev/class-code/class9:

```bash
make test-429
make test-503
make test-saturation LAB_REQUESTS=256 LAB_CONCURRENCY=64
make test-overflow LAB_REQUESTS=256 LAB_CONCURRENCY=64 LAB_OVERFLOW_LIMIT=20
make superlinked-usage
```

The final test needs Superlinked credentials in the Mac's .env. Exact counts
vary with timing and load. TARGET OBSERVED requires kv_free for the saturation
experiment, and successful kv_free fallback for the overflow experiment.
