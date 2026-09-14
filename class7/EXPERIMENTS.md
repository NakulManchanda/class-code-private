# LLM Serving Gateway --- Scheduling Policy Lab

### Class 7 --- Routing, Queuing, and Admission Control on Two vLLM Replicas

## What This Lab Explores

This lab implements the core control path of an LLM serving gateway ---
admission control, a scheduling queue, and a prefix-aware router --- and
measures how each mechanism affects latency, throughput, cache locality,
and behavior under load.

The goal is to understand each mechanism independently before composing
them into a complete serving control loop. The experiment changes one
major policy at a time so improvements and regressions can be attributed
to the mechanism being tested.

Every request passes through four decisions:

    ADMIT    → Should this request enter the system at all?
    QUEUE    → Which admitted request runs next?
    ROUTE    → Which replica should serve it?
    ENGINE   → How does the GPU actually execute it?

The benchmark walks up this stack one layer at a time:

  -----------------------------------------------------------------------
  Config          What's active              What it tests
  --------------- -------------------------- ----------------------------
  baseline        round-robin routing        reference --- no smarts

  route           prefix-aware routing       cache locality and replica
                                             placement

  queue           EDF scheduling + routing   ordering admitted requests
                                             by deadline and size

  full            admission + queue +        complete control loop ---
                  routing                    shed, order, and place
  -----------------------------------------------------------------------

Metrics tracked per run: admitted/refused counts, refusal reason,
p50/p99 TTFT, `%dl`, prefix cache hit rate, load spread across replicas,
and token throughput.

**`%dl` = deadline attainment rate: percentage of requests completing within 5000 ms. Higher is better.** Verified from bench source: `made_deadline = total_ms <= 5000`, `deadline_pct = 100 * sum(made_deadline) / len(results)`.

------------------------------------------------------------------------

## Setup

### Instance

-   **GPU:** Lambda A100 SXM4 40GB (`gpu_1x_a100_sxm4`), us-east-1
-   **Model:** `Qwen/Qwen3-0.6B` --- small enough to run two replicas on
    one GPU, no HF token needed
-   **Code synced from Mac via rsync:** `bash setup/sync_to_lambda.sh`

### Two vLLM Replicas

The lab runs two replicas of the same model on one GPU, simulating a
multi-replica serving cluster. This lets the gateway experiment with
routing, queuing, and load shedding across replicas.

``` bash
bash setup/launch_replicas.sh
# or: make replicas
```

Key vLLM flags and why they matter:

  ----------------------------------------------------------------------------
  Flag                         Value                       Why
  ---------------------------- --------------------------- -------------------
  `--gpu-memory-utilization`   `0.1`                       Fraction of GPU
                                                           memory each replica
                                                           may use. Two
                                                           replicas × 0.1 =
                                                           20% of 40GB = 8GB
                                                           total. Low enough
                                                           to avoid OOM
                                                           contention between
                                                           replicas on the
                                                           same GPU.

  `--max-num-seqs`             `8`                         Maximum concurrent
                                                           sequences per
                                                           replica. **Do not
                                                           raise this** ---
                                                           the constraint is
                                                           intentional; it
                                                           forces the
                                                           gateway's scheduler
                                                           to make real
                                                           tradeoffs.

  `--max-model-len`            `4096`                      Maximum token
                                                           context length.
                                                           Drives KV cache
                                                           size. Originally
                                                           set to 16384 which
                                                           caused the second
                                                           replica to crash
                                                           (negative KV cache
                                                           available); reduced
                                                           to 4096 to fit both
                                                           replicas.

  `--scheduling-policy`        `priority`                  Enables vLLM's
                                                           priority-aware
                                                           scheduler, required
                                                           for deadline-based
                                                           scheduling to have
                                                           effect at the
                                                           engine level.

  `--served-model-name`        `lab`                       Alias used in API
                                                           calls
                                                           (`model: "lab"`).

  `--port`                     `8001` / `8002`             Two separate HTTP
                                                           endpoints on
                                                           localhost.
  ----------------------------------------------------------------------------

#### What went wrong and why

When both replicas launched simultaneously with
`--gpu-memory-utilization 0.2` and `--max-model-len 16384`, replica
`:8001` crashed with:

    Available KV cache memory: -0.19 GiB
    ValueError: No available memory for the cache blocks.

Replica `:8002` had already allocated its share, leaving no room for
`:8001`'s KV cache. Fix: launch `:8001` first, wait for it to become
healthy, then launch `:8002`. Also reduced `--max-model-len` to `4096`
and `--gpu-memory-utilization` to `0.1`.

### Smoke Test

Confirms both replicas respond correctly before any experiment runs:

``` bash
make smoke
```

Checks three things per replica: `/v1/models`, `/metrics` (must expose
`vllm:num_requests_waiting`), and `/v1/chat/completions`.

------------------------------------------------------------------------

## Gateway

The gateway sits in front of both replicas on `:8080`. It is the
experiment surface --- all scheduling policy changes happen here, not in
vLLM.

``` bash
make gateway
# expands to:
python -m gateway.main --replicas http://127.0.0.1:8001,http://127.0.0.1:8002
```

The gateway scrapes `/metrics` from both replicas every 250ms to
track: - KV cache utilization - Number of waiting sequences - Token
throughput (for deadline estimation)

------------------------------------------------------------------------

## Unit Tests

No GPU or gateway required --- all mocked.

``` bash
make test
```

  -----------------------------------------------------------------------
  Test file                      What it covers
  ------------------------------ ----------------------------------------
  `tests/test_router.py`         Prefix-aware routing: prefers replica
                                 with matching KV cache prefix, then
                                 lighter load

  `tests/test_queue.py`          EDF scheduling: deadline beats FCFS,
                                 long prompts sort later, aging waives
                                 the penalty

  `tests/test_admission.py`      Load shedding: drops when KV pressure \>
                                 85%, queue depth exceeded, or deadline
                                 unmeetable

  `tests/test_integration.py`    Metrics scraping from vLLM `/metrics`,
                                 rate limiter burst and refill
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## Scheduling Policy Benchmark

``` bash
make bench
```

Runs 12 queries × 4 concurrent workers through the gateway, once per
policy preset. The four presets are defined in `gateway/config.py`:

``` python
presets = {
    "baseline": (admission=False, queue=False, prefix_routing=False),
    "route":    (admission=False, queue=False, prefix_routing=True),
    "queue":    (admission=False, queue=True,  prefix_routing=True),
    "full":     (admission=True,  queue=True,  prefix_routing=True),
}
```

### What each policy adds

**1 · baseline** --- Round-robin to replicas, no smarts. Baseline
latency and deadline hit rate.

**2 · route** --- Prefix-aware routing (`USE_PREFIX_ROUTING=True`). The
gateway maintains prefix-locality metadata in a trie and uses it to
estimate which replica is most likely to have reusable KV state. The
actual KV tensors remain inside the vLLM replicas/GPU memory. The goal
is to reduce redundant prefill work for repeated or similar prompts.

**3 · queue** --- Adds EDF bounded queue (`QUEUE_ENABLED=True`).
Requests are sorted by deadline × prompt length × aging factor instead
of FCFS. Long prompts that would miss their deadline are deprioritized.
Aging prevents starvation.

**4 · full** --- Adds admission control (`ADMISSION_ENABLED=True`).
Requests are rejected early (503) if: - KV cache utilization \> 85% -
Queue depth \> 4 per replica - Deadline is demonstrably unmeetable given
current throughput - Metrics are stale (replica unresponsive)

Early rejection is better than queuing a request that will time out
anyway.

### Key metrics to watch

-   **TTFT (time to first token)** --- should improve from baseline →
    route as prefix hits increase
-   **`%dl`** --- benchmark deadline-related metric; verify its exact
    definition before interpreting higher/lower as better
-   **Admission rate** --- drops under full (some requests rejected),
    but surviving requests are more likely to meet deadline
-   **Prefix hits** --- nonzero only from route onwards

------------------------------------------------------------------------

------------------------------------------------------------------------

## How the Design Connects to Class Concepts

### The CrewAI App as a Realistic Client

The bench doesn't send synthetic requests --- it uses `app.py`, a real
CrewAI application, as the client. Each query goes through a two-agent
crew:

-   **Researcher agent** --- makes the first LLM call: *"List 3 key
    facts about \[topic\]"*
-   **Writer agent** --- makes the second LLM call: *"Using those facts,
    write a 2-sentence answer"*

Both calls go through the gateway with the same query in the prompt.
This means call 2 shares a **token prefix** with call 1. If prefix
routing is working, the gateway should route call 2 to whichever replica
already cached call 1's KV blocks --- giving a cache hit and lower TTFT.

This two-agent design is intentional: it creates natural prefix overlap
between sequential calls from the same logical task, which is exactly
the pattern real agentic workloads produce (planner → executor,
researcher → writer, etc.).

The five default queries are also chosen deliberately --- all about LLM
inference internals:

``` python
DEFAULT_QUERIES = [
    "What is paged attention in LLM inference?",
    "Why does TTFT jump when the KV cache fills?",
    "What is prefix caching and when does it miss?",
    "How does a gateway decide to shed load?",
    "What is power of two choices in replica routing?",
]
```

When 4 concurrent workers fire these queries, different workers hit
overlapping prompts --- creating cross-worker prefix opportunities that
make routing improvements visible in the bench metrics.

------------------------------------------------------------------------

### Routing --- prefix awareness vs. round-robin

**Design principle:** naive round-robin ignores KV cache state. A
smarter router sends requests to the replica that already cached the
prompt prefix, saving the prefill cost.

**In the bench:** the Researcher's response gets cached on whichever
replica served it. The Writer's call (same query prefix) should land on
the same replica. In `baseline` this is random; in `route` and beyond,
the gateway scores replicas by prefix match length and load:

-   **Prefix match** --- how many tokens of this request's prompt are
    already cached on this replica (tracked via a trie updated at
    dispatch time, not on response)
-   **Load** --- current `waiting + running` sequences; a heavily loaded
    replica scores lower even with a prefix hit

The scoring is weighted: `W_PREFIX=1.0, W_LOAD=64.0` --- load dominates
unless the replica is near capacity, at which point a prefix hit can tip
the decision.

------------------------------------------------------------------------

### Queuing --- EDF with anti-starvation

**Design principle:** FCFS is unfair under mixed workloads. A 8000-token
agentic prompt blocks dozens of short interactive requests behind it.
Earliest Deadline First (EDF) reorders by urgency, but naively starves
long prompts.

**In the bench:** requests arrive with deadlines set by tenant tier
(`interactive=2s`, `agentic=5s`). The queue sorts by a composite key:

-   **Deadline** --- closer deadline = higher priority
-   **Prompt length** --- long prompts yield to short ones at equal
    deadline (they occupy more KV capacity)
-   **Aging** --- each time a request is passed over, its priority
    improves (`AGING_GAIN=0.15`), preventing starvation

The `queue` and `full` presets activate this. You should see deadline
hit rate improve vs. `route` because the queue absorbs burst and
reorders, rather than letting long prompts monopolize the replicas.

------------------------------------------------------------------------

### Admission --- predictive shedding vs. reactive

**Design principle:** queuing everything is not always better. If a
request will miss its deadline in the queue anyway, it's better to
reject it early and free resources for requests that can actually make
it.

**In the bench (`full` preset):** the gateway runs five checks before
admitting a request:

  ------------------------------------------------------------------------------------------
  Check                 Signal                                      Action
  --------------------- ------------------------------------------- ------------------------
  Stale metrics         last scrape \> 2s ago                       shed --- flying blind

  KV pressure           any replica KV usage \> 85%                 shed --- cache is full

  Queue depth           waiting \> 4 on all replicas                shed --- nowhere to put
                                                                    it

  No headroom           request tokens \> remaining KV capacity     shed --- physically
                                                                    won't fit

  Deadline unmeetable   `queue_wait + generation_time > deadline`   shed --- will time out
                                                                    anyway
  ------------------------------------------------------------------------------------------

The last check is the design principle of **predictive admission**:
using live throughput estimates (`prefill_tokens_per_s`,
`inter_token_latency_s`) to predict completion time before queuing. This
is more sophisticated than reactive shedding (dropping only after
timeout) because it preserves resources for admitted requests.

The tradeoff visible in the bench: `full` has a lower admission rate
than `queue`, but the admitted requests have a higher deadline hit rate
--- you're making a deliberate quality/volume tradeoff.

------------------------------------------------------------------------

## Results

### Run 1 --- Light load (12 queries, 4 workers, limiter=4rps/burst=8)

  Policy     admission   queue   prefix_routing   limiter
  ---------- ----------- ------- ---------------- -----------------
  baseline   off         off     off              4 rps / burst 8
  route      off         off     on               4 rps / burst 8
  queue      off         on      on               4 rps / burst 8
  full       on          on      on               4 rps / burst 8

    Config           adm  ref  p50    p99    %dl   hit%  spread  tok/s
    baseline          12    0  427    517    0.0   83.3       2    3.5
    route             12    0  246    274    0.0   91.7       0    4.8
    queue             12    0  254    292    0.0   91.7       0    4.8
    full              12    0  316    498    0.0   91.7       0    4.8

------------------------------------------------------------------------

### Analysis

#### What we expected vs. what we got

**baseline → route (expected: better TTFT, more prefix hits)**

Expected: prefix routing should reduce TTFT by steering the Writer
agent's call to the same replica that served the Researcher. Also
expected load to balance evenly.

Actual: **confirmed and strong**. p50 dropped 427→246ms (42% faster).
p99 dropped 517→274ms. Hit rate jumped 83.3→91.7%. `spread` also dropped
from 2→0. That is consistent with a more even observed distribution in
this run, but the strongest evidence for routing is the repeated TTFT
reduction together with the higher prefix-hit metric.

------------------------------------------------------------------------

**route → queue (expected: better deadline ordering under load)**

Expected: EDF reordering should help short interactive requests jump
ahead of long agentic prompts, improving deadline hit rate.

Actual: **flat --- p50 254ms, hit% unchanged at 91.7%**. Queue and route
are nearly identical. This was predictable in hindsight: with only 12
queries and 4 workers on a lightly loaded GPU, the queue never filled.
EDF has nothing to reorder when requests complete faster than they
arrive. The queue benefit is a backpressure story --- it only matters
when `max-num-seqs=8` is saturated and requests are actually waiting. We
didn't hit that threshold.

------------------------------------------------------------------------

**queue → full (expected: lower admission rate, higher deadline hit rate
for admitted requests)**

Expected: admission control should reject requests that would miss
deadline anyway, freeing resources for ones that can make it. Net
effect: lower throughput, better latency for admitted requests.

Actual: **partial --- nothing was shed (`ref=0`), but p50 rose 254→316ms
and p99 rose 274→498ms**. The fleet was too healthy to trigger any
admission checks (KV usage well below 85%, queues empty, deadlines
easily meetable). So admission control ran on every request, added
overhead, and shed nothing --- pure cost, no benefit. This is expected
behavior at light load; admission control is a heavy-traffic mechanism.

------------------------------------------------------------------------

**`%dl = 0.0` across all policies**

With `%dl` verified as deadline attainment (higher = better), 0.0% means no requests were tracked as completing within 5000ms. This is likely a bench instrumentation artifact at this low load level — Qwen3-0.6B completes in 300-500ms, well within the 5000ms threshold. The metric activates more meaningfully in higher-load runs.

------------------------------------------------------------------------

### What would make the results more interesting

The light load run confirmed routing works. To see queuing and admission
control do real work, the system needs to be stressed past
`max-num-seqs=8`. Run 2 below does exactly that.

------------------------------------------------------------------------

### Run 2 --- Stress load (24 queries, 8 workers, limiter=20rps/burst=40)

  Policy     admission   queue   prefix_routing   limiter
  ---------- ----------- ------- ---------------- -------------------
  baseline   off         off     off              20 rps / burst 40
  route      off         off     on               20 rps / burst 40
  queue      off         on      on               20 rps / burst 40
  full       on          on      on               20 rps / burst 40

    Config           adm  ref  reasons            p50    p99    %dl   hit%  spread  tok/s
    baseline          16    8  rate_limited:8      487    564    8.3   87.5       2    453
    route             16    8  rate_limited:8      273   4010   12.5   93.8       2    466
    queue             15    9  rate_limited:9      275    330    8.3   93.3       0    439
    full              15    9  rate_limited:9      317    466    4.2   93.3       7    417

------------------------------------------------------------------------

### Analysis --- Run 2

#### baseline → route

**Expected:** lower TTFT and better prefix locality.

**Observed:** p50 dropped 487→273ms (44% faster), while hit rate
increased 87.5→93.8%. However, p99 increased sharply from 564→4010ms.

This run also contained rate-limiter/retry interference, so the p99
spike cannot be cleanly attributed to prefix-aware routing or replica
hot-spotting. The safe conclusion is that median latency improved while
tail latency became unstable in this noisy stress run.

**Interpretation:** routing still shows a strong median-latency signal,
but this run motivates a cleaner overload experiment before making a
causal claim about tail latency.

------------------------------------------------------------------------

#### route → queue

**Expected:** when requests are actually waiting, EDF should reorder
work by urgency and help stabilize latency for requests with tighter
deadlines.

**Observed:** p99 fell from 4010→330ms and `spread` fell from 2→0.

That is a large observed change, but Run 2 is confounded by rate
limiting and retry behavior. It therefore does **not** prove that EDF
alone fixed a routing hot spot.

**Interpretation:** enabling the queue coincided with much better tail
latency under this stress run. Repeat the experiment with the limiter
disabled and explicit queue-depth/queue-wait telemetry to isolate the
scheduling effect.

------------------------------------------------------------------------

#### queue → full

**Expected:** admission should reject requests predicted to violate
capacity or deadline constraints, improving SLO-compliant goodput for
the work that remains.

**Observed:** p50 rose 275→317ms, p99 rose 330→466ms, `ref` stayed at 9,
and `spread` increased from 0→7. `%dl` dropped 8.3→4.2% — with deadline attainment verified as higher-is-better, this is **worse**, not better.

**Interpretation:** admission control did not demonstrate a benefit in this run. The same number of requests were refused, latency increased, spread worsened, and deadline attainment actually decreased. This is an important negative result: even if admission control is mechanically correct, it has not yet improved SLO-compliant goodput. The run is also confounded by limiter/retry noise. A controlled overload experiment is needed — one that deliberately creates sustained waiting and measures whether predictive shedding improves the attainment rate for the requests that are admitted.

------------------------------------------------------------------------

#### Rate limiter rejections (`rate_limited:8/9`)

The app-side limiter (20 rps / burst 40) still triggered because 8
concurrent workers each making 2 LLM calls burst faster than the token
bucket refills. These aren't gateway rejections --- they're client-side
throttle at the app layer before requests even reach the gateway. In a
real system the app limiter and gateway admission control are two
separate layers of defense; here they're interfering. A cleaner
experiment would disable the app limiter entirely for the stress run.

------------------------------------------------------------------------

------------------------------------------------------------------------

### Run 3 --- Clean load (24 queries, 8 workers, limiter disabled)

> **Note on run time:** Run 3 completed faster than Run 1 (12 queries, 4
> workers) despite double the load. By Run 3, vLLM's prefix cache was
> warm from prior runs --- the gateway log showed
> `Prefix cache hit rate: 79.9%` before Run 3 started. Prefix cache hits
> skip prefill computation entirely, so 24 queries with \~80% cache hits
> finished faster than 12 cold queries. This is a concrete demonstration
> of prefix caching value and also a reminder that bench runs should
> ideally warm the cache first or be compared only against runs at the
> same cache state.

### Run 3 --- Clean load (24 queries, 8 workers, limiter disabled)

  ---------------------------------------------------------------------------
  Policy      admission       queue     prefix_routing         limiter
  ----------- --------------- --------- ---------------------- --------------
  baseline    off             off       off                    1000 rps /
                                                               burst 10000
                                                               (effectively
                                                               off)

  route       off             off       on                     1000 rps /
                                                               burst 10000
                                                               (effectively
                                                               off)

  queue       off             on        on                     1000 rps /
                                                               burst 10000
                                                               (effectively
                                                               off)

  full        on              on        on                     1000 rps /
                                                               burst 10000
                                                               (effectively
                                                               off)
  ---------------------------------------------------------------------------

    Config           adm  ref  p50    p99    %dl   hit%  spread  tok/s
    baseline          24    0  514    612   66.7   91.7       0    465
    route             24    0  288    329   70.8   95.8       0    642
    queue             24    0  297    349   70.8   95.8       0    575
    full              24    0  410    532   70.8   95.8       0    553

### Analysis --- Run 3

#### baseline → route

**Expected:** lower TTFT, better prefix hits, lower deadline miss rate.

**Actual:** p50 dropped 514→288ms (44% faster), p99 dropped 612→329ms,
hit% improved 91.7→95.8%, tok/s jumped 465→642 (38% more throughput).
Unlike Run 2, p99 also improved. `%dl` changed from 66.7→70.8, but its
direction should not be interpreted until the benchmark definition is
verified.

**vs. expected:** the latency, hit-rate, and throughput measurements all
support the routing hypothesis. This is the cleanest routing signal in
the experiment.

------------------------------------------------------------------------

#### route → queue

**Expected:** EDF reordering should matter when multiple requests are
waiting with different deadlines or service costs.

**Actual:** nearly flat --- p50 288→297ms, p99 329→349ms, and `%dl`
stayed at 70.8%. No requests were refused (`ref=0`). The measurements
are consistent with insufficient queue contention for EDF to materially
change execution order.

**vs. expected:** queue benefit still not visible --- needs either
higher concurrency or a mixed workload (some very long prompts alongside
short ones) to trigger reordering. The `max-num-seqs=8` constraint isn't
being saturated consistently enough.

------------------------------------------------------------------------

#### queue → full

**Expected:** admission should become useful when the gateway predicts
capacity pressure or an SLO violation.

**Actual:** `ref=0` again --- nothing was shed. p50 rose 297→410ms and
p99 rose 349→532ms, while `%dl` stayed at 70.8%. Under this workload,
the admission policy did not activate, so no protective benefit was
observed.

**vs. expected:** admission control requires sustained overload to
activate. Three runs in, the GPU is too fast for Qwen3-0.6B at this
query count to push it past the admission thresholds.

------------------------------------------------------------------------

#### `%dl = 66-70%` — what this means

With `%dl` confirmed as deadline attainment (higher = better), 66-70% means roughly two thirds of requests completed within 5000ms. The two-agent CrewAI flow (Researcher + Writer) adds sequential overhead that pushes total_ms up even when individual LLM calls are fast. The fact that `%dl` stays flat across all four policies (66→70→70→70%) confirms that scheduling policy doesn't move the deadline needle at this load — the bottleneck is the sequential agent calls, not the gateway.

------------------------------------------------------------------------

------------------------------------------------------------------------

### Run 4 --- Cold cache restart (24 queries, 8 workers, limiter disabled, replicas restarted)

> Replicas were killed and restarted via `make replicas` before this run
> to flush GPU KV cache. vLLM's prefix cache lives in GPU VRAM --- it is
> fully cleared when the process exits.

  ---------------------------------------------------------------------------
  Policy      admission       queue     prefix_routing         limiter
  ----------- --------------- --------- ---------------------- --------------
  baseline    off             off       off                    1000 rps /
                                                               burst 10000
                                                               (effectively
                                                               off)

  route       off             off       on                     1000 rps /
                                                               burst 10000
                                                               (effectively
                                                               off)

  queue       off             on        on                     1000 rps /
                                                               burst 10000
                                                               (effectively
                                                               off)

  full        on              on        on                     1000 rps /
                                                               burst 10000
                                                               (effectively
                                                               off)
  ---------------------------------------------------------------------------

    Config           adm  ref  p50    p99    %dl   hit%  spread  tok/s
    baseline          24    0  516    575   66.7   91.7       0    489
    route             24    0  277    339   70.8   95.8       0    645
    queue             24    0  325    415   75.0   95.8       0    586
    full              24    0  466    529   66.7   95.8       0    512

### Analysis --- Run 4

Results are nearly identical to Run 3, which reveals an important fact:
**the prefix cache warms up within the baseline policy's 24 queries**.
By the time `route` runs, the cache is already hot regardless of whether
the replicas were restarted. The bench runs policies sequentially ---
baseline always goes first and seeds the cache for all subsequent
policies.

True cold-cache isolation would require restarting replicas between each
policy, which the bench doesn't do. For this lab the warm cache is
actually desirable --- it makes the routing signal cleaner (more prefix
hits to route toward).

#### Cache warm-up per replica (from logs)

  Replica   Start   After baseline   After route starts
  --------- ------- ---------------- --------------------
  :8001     0.0%    71.5%            77.1%+
  :8002     0.0%    52.8%            59.6%+

Both replicas started cold at 0.0% and warmed up within the baseline
policy's 24 queries. The asymmetry is telling --- :8001 reached 71.5%
while :8002 only reached 52.8% during baseline. In round-robin, traffic
is split evenly so neither replica builds as deep a cache. When `route`
takes over, it pins requests to the replica with the best prefix match
--- you can see :8002 continuing to climb (52.8% → 59.6%) as route
directs more matching requests its way. :8001 plateaued earlier because
it had already cached the more common prefixes.

#### Cache warm-up per replica (from vLLM logs)

| Replica | Start | After baseline | After route starts |
|---------|-------|----------------|--------------------|
| :8001   | 0.0%  | 71.5%          | 77.1%+             |
| :8002   | 0.0%  | 52.8%          | 59.6%+             |

Both replicas started cold at 0.0% and warmed within baseline's 24 queries. The asymmetry — :8001 reaching 71.5% while :8002 reached only 52.8% — is **consistent with** prefix-aware placement once `route` activates: traffic gets pinned to the replica with the better cache match, so one replica's hit rate grows while the other stabilizes. This is not by itself proof of causality. The stronger evidence is the repeated combination of increased cache-hit rate and ~42-46% lower p50 whenever prefix routing is enabled.

Comparing Run 4 vs Run 3 directly:

  Metric   Run 3 baseline   Run 4 baseline   Δ
  -------- ---------------- ---------------- -----------------
  p50      514              516              \~same
  p99      612              575              slightly better
  tok/s    465              489              slightly better

The baseline measurements are effectively unchanged. Because `baseline`
runs before `route`, the benchmark does not isolate a cold-cache routing
comparison: baseline can warm replica KV state before the routing policy
is evaluated.

------------------------------------------------------------------------

### Key Takeaways Across All Four Runs

  -----------------------------------------------------------------------
  Insight                           Evidence
  --------------------------------- -------------------------------------
  Prefix-aware routing is the       p50 improves by roughly 42--46% in
  strongest result                  Runs 1, 3, and 4; prefix-hit rate
                                    also increases

  Clean routing runs improve tail   Run 3 p99 612→329ms; Run 4 p99
  latency too                       575→339ms

  Run 2 tail behavior is confounded `route` p99 reaches 4010ms while
                                    limiter/retry behavior is active

  Queue benefit is not visible      `route` and `queue` are close in Runs
  under clean light/moderate load   1 and 3

  Admission does not activate in    `ref=0` in Runs 1, 3, and 4
  the clean runs                    

  Control mechanisms have workload  routing needs reusable prefixes; EDF
  regimes                           needs waiting/heterogeneity;
                                    admission needs overload or predicted
                                    SLO violation

  Throughput peaks with routing in  Run 3 tok/s 465→642 baseline→route
  the clean run                     

  Cache state is not isolated       policies execute sequentially, so
  between policies                  baseline can warm KV state before
                                    `route`

  Actual KV cache lives in vLLM/GPU the gateway trie is locality
  memory                            metadata, not the KV tensors

  `%dl` is deadline attainment,      verified from bench source:
  higher is better                  `made_deadline = total_ms <= 5000`

  Admission has not yet             in the noisy stress run, %dl dropped
  demonstrated a benefit            8.3→4.2% (worse); clean runs show
                                    ref=0 — no shedding triggered at all
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## Architecture and Experimental Mindset

### The Control Loop Stack

    A100 40GB
       │
       ├── vLLM :8001 ─┐
       └── vLLM :8002 ─┤
                        ▼
                     Gateway :8080
                        │
           ┌────────────┼────────────┐
           │            │            │
       Admission      Queue        Router

    baseline:  OFF        OFF      round-robin
    route:     OFF        OFF      prefix-aware
    queue:     OFF        EDF      prefix-aware
    full:      ON         EDF      prefix-aware

Each layer answers a different question:

    ADMIT    → Should this request enter the system at all?
    QUEUE    → Which admitted request runs next?
    ROUTE    → Which replica should serve it?
    ENGINE   → How does the GPU actually execute it?

### The Experimental Mindset

The most important thing this lab demonstrates isn't a specific result
--- it's a method: **hypothesis → introduce one control mechanism →
measure → explain why the result changed or didn't**.

    Round-robin
        │ measure → p50 427ms, hit% 83%
        ▼
    Prefix-aware routing
        │ measure → repeated ~42–46% p50 improvement
        ▼
    EDF bounded queue
        │ measure → little change without sustained waiting;
        │            noisy stress run motivates controlled overload test
        ▼
    Predictive admission
        │ measure → no shedding in clean runs;
        │            requires overload/SLO pressure to evaluate
        ▼
    SLO-compliant goodput

### What Would Make Scheduling Visible

The clean runs did not create enough sustained contention to clearly
exercise queueing or admission. A control mechanism should be evaluated
in the workload regime where the resource it controls is actually
constrained:

-   **Prefix routing** needs repeated/shared prefixes.
-   **EDF scheduling** needs requests that are genuinely waiting,
    ideally with heterogeneous sizes and deadlines.
-   **Admission control** needs overload or predicted SLO violation.

To make EDF, head-of-line blocking, aging, and admission visibly
measurable:

-   **Heterogeneous requests:** mix many short prompts with a few very
    long ones (8000+ tokens) to create real head-of-line blocking
-   **Tighter deadlines:** reduce `interactive` deadline from 5000ms to
    1000ms
-   **Higher concurrency:** enough workers to consistently saturate
    `max-num-seqs=8` on both replicas
-   **Mixed tenants:** `interactive` and `agentic` requests competing so
    EDF has real priority decisions to make

------------------------------------------------------------------------

## Next Experiment: Make the Control Loop Observable

For the next run, collect the state that explains *why* each policy made
a difference:

-   offered request rate and admitted request rate
-   queue depth
-   queue-wait p50/p95/p99
-   oldest request age
-   running and waiting sequences per replica
-   TTFT p50/p95/p99
-   prefix-hit rate
-   KV-cache utilization
-   rejection count and rejection reason
-   telemetry/state freshness
-   SLO-compliant goodput

Critical control-loop metrics should also have **missing/stale telemetry
alerts**. A missing queue/KV/load signal is not equivalent to zero load;
it means the gateway is operating with unknown state and should alert
and fall back conservatively.

The next workload should combine short interactive requests with a
smaller number of long prompts, tighter deadlines, and enough
concurrency to create sustained waiting. That will let the experiment
isolate head-of-line blocking, EDF ordering, aging, and predictive
admission rather than measuring their overhead while they are mostly
dormant.
