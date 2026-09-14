# Class 9: The Gateway & Router Story
*An instructor's guide to understanding the cluster architecture*

---

## The Challenge We're Solving

In the previous classes, you learned how to build and optimize a single vLLM instance. But what happens when one GPU isn't enough? When you need to scale? When you have multiple GPUs, multiple tenants, and complex routing requirements?

**This is where Class 9 comes in.**

---

## Act 1: Testing Without Real GPUs

### The Fake Worker: Your Local GPU Simulator

Before you risk deploying code to actual GPUs (which are expensive!), you need a **fake GPU system** to test everything locally. This is what `fakeworker` is.

> "Don't use a real GPU, test out everything on a fake GPU. This is exactly that part."

The fake worker lets you:
- ✅ Test admission policies
- ✅ Test routing policies  
- ✅ Stress-test the entire system
- ✅ Run experiments for different failure scenarios

You get the same interface and behavior as a real GPU, but running right on your laptop. It's your sandbox before production.

**In code:** `fakeworker/run.py` - Start here to see how we simulate GPU behavior.

---

## Act 2: The Gateway - Your Admission Controller

Now that you've tested locally, you need a **real gateway** to control what requests actually get processed.

### What is an Admission Controller?

Think of it like a bouncer at a club:
- Request comes in
- Gateway checks: "Are we still within our tokens per second limit?"
- If yes → admit the request
- If no → reject or queue it

The gateway is the first line of defense in your cluster.

**In code:** `gateway/admission.py` - This is where the bouncer logic lives.

---

## Act 3: Beyond Standard Metrics - The Dashboard Problem

Here's something most companies get wrong: they only track the metrics their vLLM instance gives them.

### What vLLM Gives You (Standard)
- Tokens per second ✅
- Decode speed ✅
- Prefill speed ✅
- Time to first token ✅

### What a Cluster Needs (Most People Miss This!)
- **Total requests** in the system
- **Rejected requests** (shredded by the router itself)
- **Accepted requests** (picked up by pools)
- **Tokens in flight** (how much KV is in use?)
- **KV free ratio** (how much headroom do we have?)
- **KV eviction stats** (when are we running out of space?)
- **KV transfer rate** (how fast can we move KV between pools?)

> "This is a second dashboard which I've not really seen most people in the industry building pretty well."

**Why does this matter?** Because when something goes wrong in your cluster, you need to know *where* it's breaking. Is it the gateway? The router? The KV bus?

**In code:** `gateway/metrics.py` - We're building that second dashboard here.

---

## Act 4: The Queue - Your Backpressure System

Remember the async queue from Class 8? We're bringing it back, but now it's part of a larger orchestration.

The queue handles:
- Requests that can't be processed immediately
- Backpressure (telling upstream "slow down, I'm full")
- Fair scheduling between requests

**In code:** `gateway/queue.py` - Same async pattern, now at scale.

---

## Act 5: The Communication Layer - Serving

Now we have requests in the queue. How do they get to the actual GPU?

### Serving.py: The Bridge

`serving.py` manages the conversation between your gateway and your **actual vLLM pods**:

```
Gateway (receives request)
    ↓
Queue (wait if needed)
    ↓
Serving (picks a healthy pod)
    ↓
vLLM Pod (processes request)
    ↓
Response (back through the chain)
```

**In code:** `gateway/serve.py` - This is the coordinator.

---

## Act 6: The Health Watcher - Type Handling

Here's the tricky part: **How do we know which pod is actually healthy?**

Kubernetes gives us snapshots, but they're just points in time. What we need is a system that continuously watches:

### The Health Checklist

For each vLLM pod, we track:
- ✅ Is it responding to health checks?
- ✅ How many active requests are on it?
- ✅ When was it last updated?
- ✅ Has it sent metrics recently?
- ✅ Or is it **stale** (broke silently)?

```python
# Pseudo-code: what we're really doing
for pod in kubernetes.pods():
    if pod.last_metric_time < now - 5min:
        # This pod is broken, don't send it requests
        mark_as_stale(pod)
    elif pod.active_requests < pod.capacity:
        # This pod has room, we can use it
        use_pod(pod)
```

The biggest gotcha? A pod might *look* healthy but actually be broken. That's why we need continuous monitoring.

**In code:** `gateway/types.py` - Pod metadata and health decisions live here.

---

## Act 7: Configuration - Making It Flexible

You don't want to hardcode cluster behavior. Different deployments need different rules.

### What You Can Configure

- Admission thresholds (tokens per second limits)
- Queue sizes (how many requests can queue?)
- Health check timeouts
- Metrics collection intervals
- Pod selectors (which pods to use?)

**In code:** Look for YAML files in `k8s-config/gateway/` - This is where configuration lives.

> "Right now, the gateway is handling everything like as a replication itself."

This means our gateway is simple, but prepared to scale. As you grow, you might shard the gateway itself.

---

## Act 8: The Router - Intelligent Routing

The gateway admits requests. The **router** decides *which pod* gets each request.

### Router's Job

```
Request → Router → "Send to vLLM-1" or "vLLM-2"?
```

But it's smarter than round-robin:
- Prefers pods with better affinity (same tokens already loaded)
- Avoids pods that are nearly full
- Falls back to overflow (Superlinked) if all pods are busy
- Tracks KV state to minimize transfers

**In code:** `router/router.py` - The decision-making logic.

---

## Act 9: The KV Bus - Moving State Around

Here's the hard part: **vLLM keeps KV tokens in GPU memory.** When you have multiple GPUs, you might have different tokens on different GPUs.

The **KB bus** (your KV management system) handles:
- Where is each token cached?
- Can we reuse it on pod-2, or do we need to transfer it?
- When memory is full, what do we evict?

**In code:** 
- `router/kvbus.py` - The KV tracker
- `router/mooncake.py` - The distributed KV store (where tokens live)

---

## Act 10: Overflow - When Everything Is Full

Even with multiple GPUs, you might run out of capacity. That's when you **overflow** to a different system.

`router/overflow.py` sends excess requests to:
- Superlinked (vector database for semantic search)
- Or a cheaper model
- Or a queue that waits for capacity

This is graceful degradation: something is better than nothing.

---

## Act 11: The Models - Text, Vision, and Everything

Your cluster needs to know which models are available and how to use them. Here's what we're running:

### Model Configuration

- **Text Model:** Qwen 3.5 - Fast, lightweight text generation
- **Vision Model:** Qwen's Vision Language Model - Same model family, but trained to understand images
- **Local Model:** Qwen 3.5 (used for local testing and fallback)

### Why This Matters

You're not just running "a model"—you're running multiple models optimized for different tasks:
- Text queries → Qwen 3.5 (fast)
- Vision queries → Qwen VLM (understand images)
- Overflow queries → Maybe a smaller/cheaper model on Superlinked

**In code:** Look for `TEXT_MODEL`, `VISION_MODEL` in your environment variables and `.env` file.

---

## Act 12: HAMI - The Disaggregation Expert

Here's a concept that'll blow your mind: **what if you separated prefill from decode?**

### What HAMI Does

HAMI stands for (conceptually) "the thing that makes disaggregated inference work."

Its job:
1. **Slicing:** Split a request into prefill phase (process all input tokens) and decode phase (generate output tokens one-by-one)
2. **KV Sharing:** After prefill finishes on pod-1, make sure decode on pod-2 can read the KV cache from pod-1

### The Prefill→Decode Problem

In a normal vLLM setup:
```
Request → [Prefill + Decode happen on same GPU]
```

In a disaggregated setup:
```
Request → [Prefill on GPU-1] → [KV cache → Mooncake] → [Decode on GPU-2]
```

The second setup is more efficient because:
- Prefill is memory-bandwidth limited (benefit from fast GPUs)
- Decode is compute limited (can use cheaper GPUs)
- You can scale them independently

### HAMI on Lambda

When you need to expand decode size (more tokens being generated), HAMI handles resizing the decode pod's memory.

**Configuration:** Memory utilization thresholds are hardcoded in the Lambda setup scripts (we'll build a dashboard for this later!).

**In code:** 
- `setup/lambda_k3s_hami.sh` - HAMI deployment configuration
- `k8s-config/hami/` - Kubernetes configs for disaggregation

---

## Act 13: Mooncake - The KV Store

Mooncake is your **distributed KV cache manager.** It answers one question:

> "Where are these KV tokens, and can I read them?"

### What Mooncake Tracks

- Which GPU has which KV tokens cached
- Can we reuse tokens from a previous request?
- When we need to move KV tokens between GPUs, how fast can we do it?
- When memory is full, what should we evict?

### Mooncake in Your Cluster

The router talks to Mooncake constantly:
- "Does GPU-2 already have tokens from request X?"
- If yes → reuse and save compute
- If no → start fresh (but maybe transfer KV from GPU-1)

**In code:** 
- `router/mooncake.py` - KV store logic
- Listens on a gRPC port (defined in `.env` as `MOONCAKE_URL`)

---

## Act 14: The Router Ports & Protocols

Your router is the orchestrator. Here's what it's doing:

### Port 8000: The Main Interface

```
[Gateway] → Router (port 8000) → [Decode Pod]
                              → [Prefill Pod]
                              → [Overflow]
```

The router sits on port 8000 and listens for:
- New requests from the gateway
- Health updates from vLLM pods
- KV cache status from Mooncake

### Inside the Router

The router has several sub-components:
- **KV Bus:** Tracks and evicts KV tokens
- **Mooncake Client:** Queries the KV store
- **Overflow Handler:** Manages fallback requests
- **Metrics Collector:** Sends cluster health to Prometheus

**In code:** `router/router.py` - The main orchestrator.

---

## Act 15: KEDA - The Auto-Scaler

KEDA stands for **Kubernetes Event-driven Autoscaling.** It answers: "Do I need more replicas?"

### KEDA's Job

KEDA watches your cluster and automatically:
- **Scale up decode:** When decode is slow, spin up more decode pods
- **Scale up prefill:** When prefill is slow, spin up more prefill pods
- **Scale up models:** When vLLM pods are full, add more of them

It uses metrics to decide:
- How many active requests per pod?
- How much KV memory is used?
- Is latency growing?

If these metrics look bad → KEDA spins up more pods. If they look good → KEDA shuts down pods.

**Why KEDA?** Because you want your cluster to breathe. Heavy load → more pods. Light load → fewer pods (save money).

**In code:** Look for `keda-*.yaml` files in `k8s-config/` - these define the scaling rules.

---

## Act 16: The Two Errors You Need to Know

Requests fail for different reasons. Your overflow strategy depends on which one.

### Error 429: Too Many Tokens

```
Client: "Generate 1000 tokens for me"
Router: "I don't have the capacity! You asked too much."
Response: 429 (Tenant Error)
```

**What it means:** The user asked for something too expensive. Not enough KV memory, too many tokens needed.

**What happens:** Router might:
- Reject the request (tell user to ask for fewer tokens)
- Queue it (wait for capacity)
- Send to overflow with a smaller model

### Error 503: No Seats Available

```
Client: "Generate 100 tokens for me"
Router: "I only have prefill capacity, no decode!"
Response: 503 (Service Unavailable)
```

**What it means:** The cluster is completely full. No pods have space.

**What happens:** Overflow takes over—send the request to:
- Superlinked (vector database)
- Or wait in a queue
- Or tell user to retry later

### The Difference

| Error | Cause | Fix |
|-------|-------|-----|
| **429** | Request too expensive | Reduce tokens, use smaller model, or queue |
| **503** | Cluster full | Wait, add more capacity, or use fallback |

---

## Act 17: Integrating with FakeWorker

Remember the FakeWorker from earlier? The router and overflow work *closely* with it.

When you run:
```bash
make fakeworker-overflow
```

You're testing overflow behavior. The FakeWorker simulates a GPU that returns 503 errors, and the overflow handler catches them.

This lets you:
- ✅ Test overflow without real GPUs
- ✅ See how requests route under failure
- ✅ Validate your fallback strategy

**In code:** `setup/overflow_smoke.py` - Tests the overflow integration.

---

## Act 18: The Contingency Strategy - When Everything Fails

Here's the real-world scenario: **What if your entire Lambda cluster goes down?**

Most systems would just fail. But not this one.

### Your Backup Plan

```
Client Request
    ↓
Try: vLLM pods on Lambda
    ↓ [ALL DOWN]
Try: Model API endpoints (via Superlinked/overflow)
    ↓ [SUCCESS]
Response delivered (slower, but not rejected)
```

### Why This Matters

- **Lambda down:** You still respond to users (from API endpoints)
- **API down:** You still respond (from Lambda pods)
- **Both down:** You reject gracefully instead of breaking

This is production-grade thinking. **You always have a backup.**

### In Your Code

`router/overflow.py` doesn't just queue requests—it routes to actual fallback APIs if the cluster is full.

---

## Act 19: The Planner - Planning Your Routing

Here's a component you actually wrote in Class 8 (or should have!):

### What the Planner Does

The planner answers: **"Given this request and this cluster state, what's the best routing decision?"**

```
Planner Input:
  - Request type (text, vision, audio)
  - Current pod status
  - KV cache state
  - Queue depth
  
Planner Output:
  - "Send to prefill pod-1"
  - "Use decode pod-2"
  - Or "Overflow to backup"
```

### Why You Need It

Without planning, you'd just send requests randomly:
- Some pods get overloaded
- Some pods sit idle
- Requests fail unnecessarily

With planning, you're intelligent:
- Distribute load fairly
- Reuse KV tokens when possible
- Graceful overflow

### In Your Code

**`router/planner.py`** - This is the decision algorithm. If you haven't written this yet, refer back to Class 8 material!

---

## Act 20: The Pools - Where Requests Actually Live

Once the planner makes a decision, the request goes into a **pool**.

### What Are Pools?

A pool is a group of pods that serve the same purpose:
- **Prefill Pool:** Pods optimized for processing input tokens
- **Decode Pool:** Pods optimized for generating output
- **General Pool:** Regular vLLM pods (if not disaggregated)

### Why Separate Pools?

Because they have different characteristics:

| Pool | Focus | GPU Type | Throughput |
|------|-------|----------|-----------|
| **Prefill** | Memory bandwidth | A100 | 50K tok/s |
| **Decode** | Compute | H100 | 10 tok/s per request |
| **General** | Balanced | A100 | Mixed |

By splitting them, you can:
- ✅ Use cheaper GPUs for decode
- ✅ Scale each independently
- ✅ Avoid wasting expensive compute on memory-bound work

### In Your Code

**`router/pools.py`** or **`router/route.py`** - Manages which pool handles each request.

---

## Act 21: The Traces - Your System's Black Box Recorder

Every request in your cluster leaves a trace. Think of it like an airplane black box.

### What's Recorded?

For each request, we save:
- **Timing:** How long did each phase take? (prefill, decode, etc.)
- **Status:** Did it succeed, fail, timeout, or overflow?
- **Metadata:** Request ID, tenant ID, model used
- **Errors:** Was there a 429? A 503? A timeout?
- **Sentiment:** Was the tenant "noisy" (many requests) or quiet?

### Why Traces Matter

Raw metrics tell you:
- "Decode is slow"

Traces tell you:
- "Decode is slow for tenant-5 when KV cache is > 80%"
- "429 errors spike at 3pm when prefix cache is full"
- "Tenant-3 made 100 requests in 1 minute (noisy!)"

### The Trace Flow

```
Request processed by router
    ↓
[Planner records decision]
[vLLM pod records timing]
[Overflow records fallback]
    ↓
Trace saved as JSON to traces/requests.jsonl
    ↓
Eventually: Analyzed, graphed, dashboarded
```

### In Your Code

**`router/trace.py`** - Records and saves every trace.

Each line in `traces/requests.jsonl` is a complete story of one request:
```json
{
  "request_id": "req-12345",
  "timestamp": "2024-09-12T12:00:00Z",
  "model": "Qwen/Qwen2.5-3B-Instruct",
  "tenant_id": "tenant-5",
  "prefill_time_ms": 150,
  "decode_time_ms": 2500,
  "total_time_ms": 2650,
  "status": "success",
  "pod": "vllm-decode-2",
  "kv_reused": true,
  "tokens_generated": 256,
  "reason": "normal"
}
```

---

## Act 22: The Dashboard Vision - Turning Traces into Insights

Right now, traces are just JSON files. But soon (tomorrow!), you'll dashboard them.

### The Dashboard Journey

**Phase 1 (Today):** Raw traces
```
tail -n 100 traces/requests.jsonl
```

**Phase 2 (Tomorrow):** Real-time dashboard
```
curl localhost:9090/dashboard
```

Shows:
- 📊 Current load (req/sec)
- 📈 Latency histogram (p50, p95, p99)
- 🔴 Error rate (429s, 503s)
- 💾 KV cache utilization
- 🚀 Throughput (tokens/sec)
- 📱 Per-tenant metrics (noisy tenants?)

### Example Dashboard Query

"Show me all requests in the last hour where latency > 500ms"

```sql
SELECT request_id, tenant_id, decode_time_ms, kv_reused
FROM traces
WHERE decode_time_ms > 500 AND timestamp > now() - 1h
ORDER BY decode_time_ms DESC
```

This tells you immediately: **"Why is tenant-3 slow? They're not reusing KV!"**

---

## Act 23: The Setup Scripts - Two Kinds of Installations

You have two ways to install your cluster:

### Type 1: Laptop Installation (for testing)
```bash
# Already done!
make setup
make test
```

Quick, local, fake GPUs.

### Type 2: Lambda Installation (for production)
```bash
make sync        # Sync code to Lambda
make ssh         # SSH to Lambda
# Then on Lambda:
bash setup/lambda_setup.sh      # Install infrastructure
bash setup/lambda_cluster.sh    # Deploy the cluster
```

More complex, real GPUs, real Kubernetes.

The scripts handle:
- ✅ Installing k3s (lightweight Kubernetes)
- ✅ Installing Keda (autoscaling)
- ✅ Deploying vLLM pods
- ✅ Configuring the gateway & router
- ✅ Setting up Mooncake (KV store)
- ✅ Configuring monitoring

---

## Act 24: The Setup Infrastructure - What Each Script Does

### Lambda Instance Setup (vLLM Installation)

When you run `lambda_setup.sh`, it:

1. **Installs vLLM** on the Lambda instance
2. **Creates two separate vLLM instances** on the same machine
   - Instance 1: Prefill-optimized
   - Instance 2: Decode-optimized
   - Or both general (depends on configuration)
3. **Downloads the models** (Qwen, vision, etc.)
4. **Configures GPU memory** allocation between instances

This is the "raw GPU" setup phase. After this, you have two independent vLLM servers running.

### Cluster Installation (Kubernetes Setup)

When you run `lambda_cluster.sh`, it installs the orchestration layer:

```
Raw vLLM instances (from lambda_setup.sh)
    ↓
Wrapped in Kubernetes pods (by lambda_cluster.sh)
    ↓
Managed by KEDA (autoscaling)
    ↓
Coordinated by HAMI (disaggregation)
    ↓
KV tokens routed by Mooncake
    ↓
Gateway/Router makes decisions
```

What gets installed:
- ✅ **KEDA** - Watches metrics, scales pods up/down
- ✅ **HAMI** - Separates prefill from decode, handles disaggregation
- ✅ **Mooncake** - Distributed KV cache store
- ✅ **Gateway** - Admission control
- ✅ **Router** - Request routing and overflow
- ✅ **Monitoring** - Prometheus metrics collection

### Smoke Tests

Before you declare success, run smoke tests:

```bash
bash setup/smoke_sliced.sh
```

This verifies:
- ✅ All pods are healthy
- ✅ vLLM instances respond to requests
- ✅ Gateway admits requests
- ✅ Router routes correctly
- ✅ KV cache works
- ✅ Overflow fallback works

If any smoke test fails, something's broken and you'll know *exactly* where.

### Code Synchronization

Your laptop code needs to get to Lambda. That's what `sync_to_lambda.sh` does:

```bash
make sync  # Copies all your Python code to Lambda
```

Instead of manually uploading files or using FTP, this script:
- ✅ Uses rsync or scp to sync efficiently
- ✅ Only sends changed files
- ✅ Preserves file permissions
- ✅ Respects .gitignore (doesn't sync secrets)

### The Setup File Organization

```
setup/
├── lambda_setup.sh              # Install vLLM + models
├── lambda_cluster.sh            # Deploy Kubernetes
├── lambda_k3s_hami.sh          # HAMI-specific config
├── lambda_vllm.sh              # vLLM launch config
├── lambda_apply_slices.sh      # Apply disaggregation
├── smoke_sliced.sh             # Validate everything
├── smoke_lambda.sh             # Basic vLLM test
├── sync_to_lambda.sh           # Sync code to Lambda
├── ssh.sh                      # SSH shortcut
├── day2_observability.sh       # Observability setup (tomorrow!)
└── overflow_smoke.py           # Test overflow behavior
```

### Observability Setup (Coming Tomorrow)

There are scripts and code for observability (dashboards, monitoring), but you won't see the full implementation today. Tomorrow you'll learn how to:
- ✅ Set up Prometheus for metrics collection
- ✅ Create Grafana dashboards
- ✅ Query traces from your JSON logs
- ✅ Visualize cluster behavior in real-time

For now, focus on getting the cluster running. Observability comes next.

---

## Act 25: The Testing Strategy - Fake Before Real

Here's the golden rule of this class:

> "Create a fake GPU, create a fake cluster, make sure everything works perfectly. Once it's working perfectly, then you start putting it on a real GPU."

### Phase 1: Laptop Testing (Fake Everything)

```bash
make setup              # Create venv
make test               # Run unit tests
make fakeworker-soak   # Simulate load
make fakeworker-429    # Simulate tenant errors
make fakeworker-overflow # Simulate overflow
```

What you're doing:
- ✅ Testing KV transfer (without real GPUs)
- ✅ Testing overflow behavior (without real GPUs)
- ✅ Testing routing logic (without real GPUs)
- ✅ Validating all code paths work

No expensive hardware needed. Just your laptop and time.

### The Test Suite

Look at `tests/` directory:

```
test_overflow.py        # Does overflow work correctly?
test_kv_transfer.py     # Can we move KV between pods?
test_planner.py         # Does routing make good decisions?
test_fakeworker.py      # Does fake worker behave right?
test_lab.py             # End-to-end integration test
... (more tests)
```

Each test validates one piece:
- Fake workers return correct responses ✅
- Overflow catches 503 errors ✅
- KV tokens transfer correctly ✅
- Router makes smart decisions ✅
- Metrics are collected ✅

### Phase 2: Real Lambda Testing (Real Hardware)

Once all tests pass on your laptop:

```bash
make sync               # Copy code to Lambda
make ssh                # SSH to Lambda
bash setup/lambda_setup.sh    # Install vLLM + k3s
bash setup/lambda_cluster.sh  # Deploy cluster
bash setup/smoke_sliced.sh    # Validate on real GPU
```

Now you're testing with:
- ✅ Real vLLM instances (not fake)
- ✅ Real Kubernetes (not simulated)
- ✅ Real GPU memory
- ✅ Real latencies

But you've already validated the logic. You're just checking that the real hardware plays nice.

### The Smoke Tests

`smoke_sliced.sh` runs quick sanity checks:
- Does the gateway respond?
- Can the router route?
- Do vLLM pods work?
- Does KV transfer work?
- Does overflow fallback work?

If all smoke tests pass → your cluster is healthy.

---

## Act 26: The app.py - Your Interactive Interface

Once everything is deployed (laptop or Lambda), you need a way to send requests.

### What app.py Does

```python
# Start the interactive REPL
python app.py

# Now you can type:
>>> text Write one sentence about a GPU.
ROUTE: text → prefill → decode
TEXT: "GPUs enable parallel computation..."

>>> vision What color is this?
ROUTE: vision → vllm-vision
TEXT: "The color is blue"

>>> quit
```

### The Request Flow in app.py

```
User types command
    ↓
app.py parses it (text/vision/audio)
    ↓
Creates a Request object with:
  - Model type
  - Tokens to generate
  - Tenant ID
    ↓
Sends to gateway.admission
    ↓
Gateway checks: "Can we process this?"
    ↓
If yes: Router decides which pod
    ↓
vLLM generates response
    ↓
Trace saved to traces/requests.jsonl
    ↓
Response printed to terminal
```

### Inside app.py

Looking at the image, `app.py` imports everything it needs:

```python
from router.overflow import FakeOverflow, send
from router.router import Router
from gateway.admission import Gateway
from router.kvbus import KVBus
from gateway.metrics import METRICS
from router.pools import FakeWorker
from router.trace import TRACES
from gateway.types import Request
```

This is your orchestration layer. It's NOT doing the actual inference—it's coordinating:
- Admission (gateway)
- Routing (router)
- KV management (kvbus)
- Overflow (when full)
- Tracing (logging everything)

### The Request Format

When you type `text Write one sentence about a GPU.`, app.py creates:

```python
Request(
    id="req-12345",
    arrival_t=0.0,
    priority=1,
    prompt_tokens=32,
    max_new_tokens=8,
    prefix_hash=None,
    tenant="lab"
)
```

This gets passed through the entire system, and eventually you get:

```json
{
  "request_id": "req-12345",
  "status": "success",
  "response": "GPUs enable parallel computation...",
  "latency_ms": 250,
  "tokens_generated": 12,
  "pod": "vllm-decode-2",
  "kv_reused": false
}
```

### Why app.py Matters

It's your testing harness. You can:
- ✅ Send different request types (text, vision, audio)
- ✅ See routing decisions in real-time
- ✅ Trace every request through the system
- ✅ Validate the entire pipeline works

It's not production—it's interactive exploration. But it teaches you everything about how your cluster works.

### app.py as Your Foundation

Here's the powerful part: **app.py isn't just for testing.** It's the foundation for your real application:

#### Option 1: Interactive REPL (Today)
```bash
python app.py
>>> text Write about GPUs
ROUTE: ...
TEXT: ...
```

#### Option 2: Crew AI Agent (Tomorrow)
Instead of a simple REPL, wrap it in CrewAI:
```python
from crewai import Agent, Crew

agent = Agent(
    role="AI Assistant",
    goal="Help users with information",
    tools=[call_gateway]  # Use our gateway!
)
```

The agent routes through your gateway.

#### Option 3: RAG Application
Build a retrieval-augmented generation app:
```python
def rag_query(question):
    docs = retrieve_docs(question)
    context = "\n".join(docs)
    request = Request(prompt=f"{context}\n{question}")
    return gateway.process(request)
```

#### Option 4: REST Endpoint
Expose it as an API:
```python
@app.post("/query")
async def query(text: str):
    request = Request(prompt=text)
    response = gateway.process(request)
    return response
```

### The Key Insight

All of these options use the **same underlying gateway and router**. You're just changing the interface:
- REPL: User types commands
- Crew: Agent makes decisions
- RAG: Retriever feeds context
- API: HTTP clients send requests

The cluster doesn't care. It just processes requests.

This is why separating concerns matters:
- **Gateway/Router/vLLM:** The engine (unchanging)
- **app.py:** The interface (flexible)

You can swap out the interface without touching the engine.

---

---

## Act 27: The Lambda Architecture Decision - One Instance with Two Replicas

Here's a real-world constraint that shaped the design:

### The Question
> "Do we need two separate Lambda instances, or one instance with two parts?"

### The Constraint
A single Lambda GPU instance has **40GB of memory**. Running two complete vLLM instances would require:
- vLLM instance 1: ~20GB
- vLLM instance 2: ~20GB
- Kubernetes + services: ~5GB
- **Total: ~45GB** ❌ (over budget!)

### The Solution
**One Lambda instance with two VLLM processes:**

```
Single 40GB GPU Instance
├── VLLM Prefill Process (port 8000)
│   ├── Model weights: ~10GB
│   └── KV cache: ~8GB (dynamic)
├── VLLM Decode Process (port 8001)
│   ├── Model weights: ~10GB
│   └── KV cache: ~8GB (dynamic)
└── Kubernetes + Gateway/Router: ~2GB
```

Total: ~38GB ✅ (fits!)

### Why This Teaches You More

By separating prefill and decode on the **same instance**, you learn:
1. **Disaggregation:** How to split request phases
2. **KV Management:** How tokens move between processes
3. **Memory Pressure:** What happens when KV cache fills
4. **Efficiency:** Why separating concerns matters

If you had two complete instances, you'd miss the interplay between them.

### Real-World Scaling

In production with unlimited budget:
- Prefill pods on A100s (memory-bandwidth optimized)
- Decode pods on H100s (compute optimized)
- Each scales independently

But for this class, we're simulating that with two processes on one GPU.

---

## Act 28: Understanding the 40 Tests - What Each One Validates

You've got 40 tests. Here's what each group tests:

### Test Categories

**test_bind_capability.py** (6 tests)
- Does your router understand request types?
- Can it bind a "text request" vs "vision request" vs "audio request"?
- Does it know which model handles which?

**test_cluster_scripts.py** (2 tests)
- Do the KEDA, HAMI, Mooncake installation scripts work?
- Can they be run without errors?

**test_epp_scorers.py** (2 tests)
- EPP = Estimated Processing Power
- Scoring: Which pod should handle this request?
- Does your scoring logic pick the right pod?

**test_fakeworker.py** (5 tests)
- Does the fake GPU behave like a real GPU?
- Does it return correct responses?
- Does it simulate errors properly?

**test_kv_transfer.py** (3 tests)
- Can KV tokens move between pods?
- Are they transferred correctly?
- Does reuse work?

**test_lab.py** (7 tests)
- End-to-end integration test
- Admission → Routing → KV → Overflow all together
- Most comprehensive test

**test_overflow.py** (4 tests)
- When the cluster is full, does overflow work?
- Does it catch 503 errors?
- Does it route to Superlinked?

**test_planner.py** (1 test)
- Does the router planner make good decisions?

**test_prefix_sticky.py** (3 tests)
- Prefix caching: Can we reuse prefixes?
- Does prefix stickiness work?

**test_shed_codes.py** (3 tests)
- Shedding: Removing requests under load
- Does it shed gracefully?

**test_vllm_worker.py** (1 skipped test)
- Tests real vLLM (skipped on laptop—needs GPU)

**test_yaml_contract.py** (3 tests)
- Kubernetes YAML files are valid
- Contract between code and k8s is satisfied

### Key Insight

Each test is **isolated**—it tests one component in isolation. When you run `make test`, you're validating that every piece works.

---

## Act 29: Fakeworker Scenarios - Testing Real Behaviors

After unit tests pass, you test with fakeworker scenarios. These simulate real-world situations:

### Scenario 1: fleet-soak
**Question:** "What happens under sustained load?"

```
Scenario: Send 20 requests rapidly to a fake GPU
Expected: 
  - Gateway admits them (up to limit)
  - Router distributes them
  - Some queue if full
  - All eventually process
```

Why this matters: Validates your cluster handles steady traffic.

### Scenario 2: tenant-429-stays
**Question:** "What if a tenant asks for too many tokens?"

```
Scenario: Send request asking for 500 tokens (very expensive)
Expected:
  - Gateway sees "this is expensive"
  - Options: queue it, reject it, or reduce tokens
  - Request doesn't disappear—handled gracefully
```

Why this matters: Shows 429 error handling works.

### Scenario 3: overflow-on-503
**Question:** "What if the cluster is full?"

```
Scenario: Fill the cluster completely, then send another request
Expected:
  - Router says "no seats available"
  - Returns 503 error
  - Overflow catches it
  - Routes to Superlinked (cheaper API)
  - User gets response anyway
```

Why this matters: Your fallback strategy works.

### Running Scenarios

Add print statements to see what happens:

```python
# In router.py or fakeworker.py
print(f"[FLEET-SOAK] Request received: {request.id}")
print(f"[FLEET-SOAK] Gateway decision: admit/queue/reject")
print(f"[FLEET-SOAK] Router decision: pod-1/pod-2/overflow")
print(f"[FLEET-SOAK] Final status: {response.status}")
```

Then run:
```bash
make fakeworker-soak
```

Watch the print statements to see your system in action!

---

## Act 30: Superlinked - Your Overflow Fallback

When your cluster is full (503 error), requests overflow to **Superlinked** - a vector database + LLM API.

### What Superlinked Does

Instead of queuing forever, Superlinked:
- Takes your request
- Processes it (slower, cheaper)
- Returns a response
- Saves your system from cascading failures

### Setting Up Superlinked

From the console.superlinked.com images you showed:

1. **API Key:** Found in console → API KEYS
   - Example: `sk-sie-MhP2p...WsUd`
   
2. **Add to .env:**
   ```bash
   export OVERFLOW_API_KEY=sk-sie-MhP2p...WsUd
   export OVERFLOW_BASE_URL=https://api.superlinked.com/v1
   export OVERFLOW_MODEL=Qwen/Qwen3.5-4B
   ```

3. **In overflow.py:**
   ```python
   # When cluster is full:
   response = superlinked_client.query(
       api_key=env.OVERFLOW_API_KEY,
       model=env.OVERFLOW_MODEL,
       prompt=request.prompt
   )
   ```

### Why Superlinked?

- ✅ Falls back when your cluster is full
- ✅ Cheaper than high-end GPUs
- ✅ Reliable API (you're not maintaining it)
- ✅ Trades latency for availability

Your users prefer "slow response" over "no response"!

---

---

## Act 31: Understanding Fakeworker Output - What the Results Tell You

When you run fakeworker scenarios, the output tells a story about your system:

### fleet-soak Output
```
fleet-soak completed=3 shed_503=17 overflow_calls=17 via_overflow=17
PASS
```

**What this means:**
- `completed=3`: Only 3 requests finished normally on the cluster
- `shed_503=17`: 17 requests got 503 errors (cluster full!)
- `overflow_calls=17`: All 17 were sent to overflow
- `via_overflow=17`: All 17 completed via Superlinked

**Story:** Your cluster received 20 requests, but only had capacity for 3. The other 17 overflowed gracefully to Superlinked. **Good!** No requests were rejected—they all got answers, just slower.

### tenant-429-stays Output
```
tenant-429-stays noisy=429 quiet=200 overflow=0
PASS
```

**What this means:**
- `noisy=429`: Request asked for too many tokens, got 429 error
- `quiet=200`: Request silently rejected (probably too expensive)
- `overflow=0`: None went to overflow

**Story:** Your admission control is working. Expensive requests get 429 errors and stay in the system (not rejected), waiting for capacity. This teaches tenants to retry or ask for fewer tokens.

### The Philosophy

These tests show your system's personality:
- ✅ Prefer overflowing to rejecting (use Superlinked as fallback)
- ✅ Don't silently drop requests—give them 429 or 503 errors
- ✅ Let expensive requests queue instead of immediately rejecting
- ✅ Track everything (shed, overflow, capacity)

---

## Act 32: run.py File Structure - Building Your Orchestrator

The `fakeworker/run.py` file is the heart of local testing. Here's what each import does:

### Imports: Setting Up the Tools

```python
from __future__ import annotations  # Type hints don't become Python code
import argparse                      # Parse command-line arguments
import io                            # Handle input/output streams
import os                            # Talk to the operating system
from contextlib import redirect_stdout  # Redirect prints to files
```

**Why these matter:**

**`from __future__ import annotations`**
- Makes type hints "lazy"
- Normally: `def foo(x: SomeType)` → Python tries to resolve `SomeType` immediately
- With `__future__`: Type hints stay as strings until needed
- Benefit: No errors if your types aren't defined yet (forward references work)

**`argparse`**
- Parses command-line arguments like `--behavior fleet-soak`
- Makes your script configurable without editing code

**`io` and `redirect_stdout`**
- Instead of printing to terminal, redirect to files
- Example: Capture all output → save to `traces/requests.jsonl`
- Benefit: You keep logs even if terminal closes

**`os`**
- Communicate with operating system
- Read/write files
- Get GPU info
- Maintain system clocks

### The Data Classes

```python
@dataclass
class BehaviorResult:
    behavior: str
    completed: int
    shed_503: int
    overflow_calls: int
    # ...
```

Instead of manually writing constructors, use `@dataclass` to auto-generate `__init__`, `__repr__`, etc.

### Request Defaults

```python
base = dict(str, str | float | None)(
    id="req",
    priority=1,
    prompt_tokens=64,
    max_new_tokens=8,
    prefix_hash=None,
    tenant="lab"
)
```

Default request for testing:
- Priority 1 (normal, not urgent)
- 64 input tokens, 8 output tokens
- Labeled as tenant "lab" (so you know it's a test)

When requests exceed these limits → eviction or errors → you learn about your cluster's behavior.

---

---

## Act 33: The Fakeworker Fleet - Creating a Fake Cluster Locally

The `_fleet()` function creates a complete fake cluster in memory. Here's what happens:

### Creating the Fake Infrastructure

```python
def _fleet(n_p: int, n_d: int, kv=8_000) -> tuple[...]:
    """Create fake prefill and decode workers with shared KV bus"""
    bus = KVBus()  # Shared KV token store
    
    # Create n_p prefill workers
    prefill = [FakeWorker(f"p{i}", kv_capacity=kv, bus=bus) for i in range(n_p)]
    
    # Create n_d decode workers
    decode = [FakeWorker(f"d{i}", kv_capacity=kv, bus=bus) for i in range(n_d)]
    
    return prefill, decode, bus
```

**What this gives you:**
- Isolated prefill and decode workers
- Shared KV bus (tokens can move between them)
- Each with 8,000 KV capacity (simulates GPU memory)
- Everything in memory—super fast for testing

### Running behavior_fleet_soak()

```python
def behavior_fleet_soak() -> BehaviorResult:
    METRICS.reset()  # Clear metrics
    
    # Create cluster: 3 prefill, 3 decode workers, 50K KV each
    prefill, decode, _ = _fleet(kv=50_000)
    
    # Create gateway with admission control
    gw = Gateway(
        Router(prefill, decode),
        tokens_per_min=10_000_000  # Limit
    )
    
    backup = FakeOverflow()  # Fallback if cluster full
    
    # Send 20 requests rapidly
    for i in range(20):
        resp = send(
            _req(i, timeout_s=1.0, prompt_tokens=32, max_new_tokens=8),
            gw,
            backup
        )
        track_result(resp)  # Record success/failure
```

**The Story:**
1. Create fake prefill/decode workers with 50K KV each
2. Wrap them in a gateway (admission control)
3. Add overflow fallback (Superlinked)
4. Fire 20 requests at it
5. Watch how it handles load:
   - How many complete normally?
   - How many get 503 (cluster full) → overflow?
   - How many get 429 (tenant error)?

### Why This Matters

You're testing your entire cluster **without real GPUs**:
- ✅ Gateway admission works
- ✅ Router picks pods correctly
- ✅ KV sharing works
- ✅ Overflow catches failures
- ✅ Metrics are collected
- ✅ All in seconds, not minutes

Then when you deploy to Lambda, you already know the logic works.

### Tracing: tenant="lab"

Every request has `tenant="lab"`. In your traces file:

```json
{"request_id": "req-1", "tenant": "lab", "pod": "p0", "status": "success", ...}
{"request_id": "req-2", "tenant": "lab", "pod": "d1", "status": "overflow", ...}
{"request_id": "req-3", "tenant": "lab", "pod": "p2", "status": "429", ...}
```

When you see `"tenant": "lab"`, you instantly know: **This was a test on the fake cluster.** Production requests will have real tenant IDs.

---

## Act 34: HTTP Error Codes - What Each One Means in Your System

Your fakeworker tests use standard HTTP error codes. Here's what each means:

### 200: Success ✅
```
Request processed normally
Response: Generated tokens
```

### 429: Too Many Requests (Tenant Error)
```
Symptom: Tenant asked for too many tokens (or too frequent requests)
Example: "Generate 1000 tokens" when limit is 256
Router says: "I CAN process this, but not right now"
Action: Queue the request, keep it in the system, wait for capacity
User sees: Request stays in queue, will complete when tokens available
```

**Why 429?** Standard HTTP code for "rate limit exceeded"

### 503: Service Unavailable (Cluster Error)
```
Symptom: Cluster is completely full, no pods have space
Example: All prefill/decode pods at capacity
Router says: "I CANNOT process this at all"
Action: Send to overflow (Superlinked)
User sees: Response from fallback service (slower but functional)
```

**Why 503?** Standard HTTP code for "service temporarily unavailable"

### The Difference

| Code | Cause | Response | User Impact |
|------|-------|----------|-------------|
| **429** | Tenant expensive | Queue | "Please wait" |
| **503** | Cluster full | Overflow | "Using backup service" |

**Key insight:** 429 means "we're not rejecting you, we're queueing you." 503 means "we're overflowing you to backup."

---

## Act 35: The _fleet() Function - Creating Test Infrastructure

The `_fleet()` function is your test harness builder:

```python
def _fleet(n_p: int, n_d: int, kv: int = 8_000):
    """
    Create a fleet of fake workers for testing
    
    Args:
        n_p: Number of prefill workers
        n_d: Number of decode workers  
        kv: KV cache capacity per worker
    """
    bus = KVBus()  # Shared KV token store
    
    # Create prefill workers (handles input token processing)
    prefill = [
        FakeWorker(f"prefill-{i}", kv_capacity=kv, bus=bus)
        for i in range(n_p)
    ]
    
    # Create decode workers (handles output token generation)
    decode = [
        FakeWorker(f"decode-{i}", kv_capacity=kv, bus=bus)
        for i in range(n_d)
    ]
    
    return prefill, decode, bus
```

**What you get:**
- `prefill`: Workers optimized for input processing (memory-bound)
- `decode`: Workers optimized for output generation (compute-bound)
- `bus`: Shared KV store—tokens can move between workers

**Example:** `_fleet(n_p=3, n_d=3, kv=50_000)`
- 3 prefill workers, each with 50K tokens of KV space
- 3 decode workers, each with 50K tokens of KV space
- All share the same KV bus

### Why Separate Prefill/Decode?

In disaggregated inference:
- **Prefill:** Process all input tokens at once → memory-bound → needs fast memory
- **Decode:** Generate one output token at a time → compute-bound → needs fast compute

By separating them, you can:
- Use fast GPUs (A100) for prefill
- Use cheap GPUs (T4) for decode
- Scale them independently

---

## Act 36: BehaviorResult - Tracking Test Outcomes

Every behavior test returns a `BehaviorResult`:

```python
@dataclass
class BehaviorResult:
    name: str              # e.g., "fleet-soak"
    passed: bool           # Did the test pass?
    completed: int         # Requests finished normally
    shed_503: int          # Requests got 503 (cluster full)
    overflow_calls: int    # Requests sent to overflow
    via_overflow: int      # Requests completed via Superlinked
    shed_429: int          # Requests got 429 (tenant error)
    quiet_rejects: int     # Requests silently rejected
```

### Reading the Results

```
fleet-soak: completed=3 shed_503=17 overflow_calls=17 via_overflow=17
```

**Translation:**
- `completed=3`: 3 requests processed on your cluster (13% success rate)
- `shed_503=17`: 17 requests got 503 (cluster full)
- `overflow_calls=17`: All 17 full requests went to Superlinked
- `via_overflow=17`: All 17 completed via Superlinked

**Story:** You sent 20 requests. Your fake cluster could only handle 3. The other 17 overflowed to Superlinked, which completed all of them. **No requests were lost—just slower.**

---

## Act 37: Testing Methodology - Sending Sequential Requests

The behavior test sends requests one at a time in a tight loop:

```python
def behavior_fleet_soak():
    # Setup
    prefill, decode, _ = _fleet(kv=50_000)
    gw = Gateway(Router(prefill, decode), tokens_per_min=10_000_000)
    backup = FakeOverflow()
    
    # Send 20 requests, one per loop iteration
    for i in range(20):
        resp = send(
            _req(i, timeout_s=1.0, prompt_tokens=32, max_new_tokens=8),
            gw,
            backup
        )
        # Track: was it completed, 503'd, 429'd, overflowed?
```

### Why Sequential?

**Option 1: Async (concurrent)**
```
Request 1 → Process immediately (fast)
Request 2 → Process immediately (fast)
Request 3 → Process immediately (fast)
Result: Easy, no contention
```

**Option 2: Sequential (one after one)**
```
Request 1 → [Process] → Completes
Request 2 → [Process] → Completes (pods now busier)
Request 3 → [No space] → 503, overflow
```

Sequential reveals what happens under real load:
- Early requests have capacity
- Later requests see a full cluster
- Shows your overflow strategy in action

### The Test Story

Sending 20 requests sequentially to a small cluster:
1. First few requests succeed (prefill/decode have space)
2. Cluster fills up gradually
3. Middle requests hit 503 (cluster full)
4. Those get overflowed to Superlinked
5. Later requests either:
   - Wait in queue (if < 429 threshold)
   - Get 429 (if too expensive)
   - Overflow (if cluster still full)

You see the whole lifecycle in one test!

---

---

## Act 38: Fleet Soak Behavior - Dumping Requests at the System

"Fleet soak" = **dump a massive number of requests concurrently at a small cluster.**

### What Happens

```
20 requests arrive simultaneously:

Time 0ms:
  Request 1-3: Land in prefill (has space)
  Request 4-20: Wait or 503

Time 100ms:
  Prefill finishes → Requests 4-6 start prefill
  Requests 1-3: Decode (has space)
  Requests 7-20: Still waiting or 503

Time 200ms:
  Decode fills up → New requests get 503
  503 → Overflow to Superlinked
  Superlinked processes them (slower, but working)
```

### The Metrics

```
fleet-soak completed=3 shed_503=17 overflow_calls=17 via_overflow=17
```

**What this tells you:**
- ✅ Gateway is working (admits requests)
- ✅ Router is working (picks pods)
- ✅ Overflow is working (catches 503s)
- ✅ Superlinked is working (completes via fallback)
- 📊 Your small cluster handles 15% of requests locally, 85% via overflow

### Why "Soak"?

The word "soak" comes from testing terminology:
- **Soak test:** Run system under heavy load for extended time
- **Stress test:** Increase load until it breaks

Here, "fleet soak" = short stress test on the fleet. You're **soaking it with requests** to see how it responds.

**Interchangeable terms:**
- "Fleet soak" = small group of servers under load
- "Cluster soak" = larger cluster under load
- Both mean: concurrent heavy request traffic

---

## Act 39: Unhealthy Pod Behavior - Autoscaling in Action

What happens when a pod dies or gets slow?

### Scenario: One Decode Pod Sick

```
You have 2 decode pods:
  Decode-0: HEALTHY ✅
  Decode-1: DOWN or SLOW ❌

Requests arrive:
  Request 1: Decode-0 takes it (has space)
  Request 2: Decode-0 takes it (has space)
  Request 3: Decode-0 full, Decode-1 sick → 503!
  Request 4: Still 503 → Overflow to Superlinked
```

### What Should Happen

**Without autoscaling:**
- You get 503 errors
- Users overflow to Superlinked
- You're stuck at this capacity

**With autoscaling (KEDA):**
1. Router detects "Decode-0 is saturated"
2. Planner says: "Can we add a Decode-1?"
3. KEDA scaler checks: "Is threshold exceeded?"
4. If yes: Spin up a new decode pod
5. New pod takes traffic
6. Saturation goes down

### The Planner's Role

`planner.py` answers: **"Given current capacity, what should we do?"**

```python
def plan_scaling(current_pods, utilization, threshold):
    """
    If any pod is over-utilized, recommend scaling
    """
    if utilization > threshold:
        return "SCALE_UP"  # Add more pods
    elif utilization < 20%:
        return "SCALE_DOWN"  # Remove idle pods
    else:
        return "STABLE"  # Keep as is
```

### How KEDA Watches

```yaml
scaledobject.keda.sh/decode-scaler
  MIN: 1 pod
  MAX: 2 pods
  TRIGGER: prometheus (check metrics)
```

KEDA continuously:
1. Reads metrics from Prometheus
2. Asks planner: "Should we scale?"
3. If utilization > threshold: Scale up to 2
4. If utilization < low threshold: Scale down to 1

### The Full Loop

```
Heavy traffic arrives
    ↓
Decode pod gets saturated
    ↓
Router detects saturation → 503 errors
    ↓
Planner checks: "Is utilization > 80%?"
    ↓
If yes: KEDA spins up Decode-2
    ↓
New pod takes traffic
    ↓
Saturation drops
    ↓
System stabilizes
```

This is why disaggregation is powerful:
- **Prefill slow?** Scale prefill independently
- **Decode slow?** Scale decode independently
- **Both?** Scale both in parallel

No wasting resources scaling the entire cluster.

---

---

## Act 40: The Planner Implementation - Making Scaling Decisions

The planner looks at current state and decides what to do:

```python
def planner(prefill_pods, decode_pods, tokens_in_flight):
    """
    Given current cluster state, decide if we need to scale
    """
    decode_utilization = tokens_in_flight / decode_capacity
    
    if decode_utilization > 0.8:
        # Decode is saturated
        if can_scale_up_decode():
            return "SCALE_DECODE_UP"
    
    prefill_utilization = tokens_in_flight / prefill_capacity
    
    if prefill_utilization > 0.8:
        # Prefill is saturated
        if can_scale_up_prefill():
            return "SCALE_PREFILL_UP"
    
    return "STABLE"
```

### Critical Rule: Never Mix Prefill and Decode

```
GPU has 40GB total:
  Prefill using: 16GB
  Decode using: 16GB
  Free: 8GB

❌ WRONG: Use the 8GB to help decode
          (they're specialized, won't help)

✅ RIGHT: Only scale decode if decode replicas can grow
         Keep prefill and decode separate
```

Why? Because:
- Prefill pods are optimized for memory bandwidth (need fast GPU memory)
- Decode pods are optimized for compute (need fast compute cores)
- Sharing GPU doesn't help if the workload is wrong for that GPU

The planner tracks:
1. **Current prefill pods** and their utilization
2. **Current decode pods** and their utilization
3. **Tokens in flight** (how busy are we?)
4. **Available replicas** (can we scale up?)

If decode is sick or saturated → scale decode only. Leave prefill alone.

---

## Act 41: behavior_unhealthy_decode_scales() - Resilience Test

This test checks: **"If one decode pod dies, what happens?"**

```python
def behavior_unhealthy_decode_scales() -> BehaviorResult:
    """
    Scenario: One decode pod is sick/down
    Expected: System detects, planner scales, 503s go down
    """
    prefill, decode, _ = _fleet(n_d=2)  # 2 decode pods
    # Simulate: Decode-1 is sick (dropped from rotation)
    
    gw = Gateway(Router(prefill, [decode[0]]))  # Only 1 pod working
    
    # Send requests
    for i in range(20):
        resp = send(_req(i), gw)
    
    # Expected: 
    # - Some requests get 503 (decode full)
    # - Planner says "scale up"
    # - New pod created
    # - 503s drop
```

**Output:**
```
unhealthy-decode-scales shed_503={n503} overflow=0 planner={out.strip()}
```

**What this means:**
- `shed_503=X`: X requests got 503 errors (cluster full)
- `overflow=0`: No overflow to Superlinked (planner fixed it)
- `planner=SCALE_DECODE_UP`: Planner recommended scaling

The test validates your system can:
- ✅ Detect unhealthy pods
- ✅ Reduce 503 errors by scaling
- ✅ Keep requests flowing without overflow

---

## Act 42: behavior_tenant_429_stays() - Tenant Error Handling

This test checks: **"How do we handle expensive tenant requests?"**

```python
def behavior_tenant_429_stays() -> BehaviorResult:
    """
    Scenario: Two requests—one expensive, one cheap
    Expected: Expensive gets 429 (stays in queue), cheap gets 200 (processed)
    """
    prefill, decode, _ = _fleet()
    
    gw = Gateway(Router(prefill, decode), tokens_per_min=40)
    
    # Request 1: Expensive (64 tokens)
    noisy = send(_req(0, tenant="noisy", prompt_tokens=64), gw)
    # -> Gets 429 (too expensive, stays in queue)
    
    # Request 2: Cheap (16 tokens)
    quiet = send(_req(1, tenant="quiet", prompt_tokens=16), gw)
    # -> Gets 200 (affordable, processes immediately)
    
    # Expected: No overflow (both stay in system)
    backup.calls == []
```

**Output:**
```
tenant-429-stays noisy=429 quiet=200 overflow=0
```

**What this means:**
- `noisy=429`: Expensive request got rejected with 429 status
- `quiet=200`: Cheap request got accepted and processed
- `overflow=0`: Nothing went to Superlinked

**The philosophy:**
- Don't reject expensive requests (they're still customers!)
- Keep them in queue with 429 status
- Let them retry or ask for fewer tokens
- This preserves fairness and gives users options

### Tenant vs. Cluster Errors

| Code | Cause | Who's responsible? | What to do |
|------|-------|-------------------|-----------|
| **429** | Request too expensive | Tenant (ask for less) | Queue it |
| **503** | Cluster full | System (scale up) | Overflow to backup |

429 = "Your request is too big for the queue"
503 = "Our cluster is too full for queuing"

---

## Act 43: behavior_ignore_stale_pod() - Detecting Broken Pods

This test checks: **"Can we ignore pods that have gone silent?"**

```python
def behavior_ignore_stale_pod() -> BehaviorResult:
    """
    Scenario: Pod A is healthy, Pod B hasn't sent metrics in 5 min
    Expected: Route all traffic to Pod A, treat Pod B as dead
    """
    bus = KVBus()
    
    # Pod A: Responsive
    a = FakeWorker("A", bus=bus)
    
    # Pod B: Stale (hasn't reported metrics)
    b = FakeWorker("B", bus=bus, last_metric_time=5_minutes_ago)
    
    router = Router([a, b])
    
    # Send requests
    for i in range(10):
        resp = send(_req(i), router)
    
    # Expected:
    # All requests go to A (B is ignored)
    # No errors, no 503s
```

**Why stale detection matters:**

A pod can appear "alive" to Kubernetes but actually be broken:
- Still running (Kubernetes sees it)
- Not responding to requests (we don't know)
- Not sending metrics (we can't track it)

Solution: **If we haven't heard from a pod in 5 minutes, treat it as dead.**

The router continuously checks:
```python
if now - pod.last_metric_time > 5_minutes:
    mark_as_stale(pod)
    stop_sending_requests_to_it()
```

This prevents requests from hitting a silent, broken pod.

---

---

## Act 44: The Stale Pod Problem - Trust But Verify

Here's a real-world issue: **A pod can look healthy but be broken.**

### The Scenario

```
Pod A: Last metric received: 10 minutes ago
       Kubernetes says: "Running ✅"
       But: Actually hung, won't accept requests

Pod B: Last metric received: 2 seconds ago
       Kubernetes says: "Running ✅"
       And: Actually healthy, accepting requests

Router gets request:
  Option 1 (Wrong): "Pod A looks older, let me use Pod B"
  Option 2 (Right): "Pod A is stale (no metrics in 5 min), 
                     trust only Pod B"
```

### The Solution: Stale Detection

```python
STALE_THRESHOLD = 5_minutes

for pod in cluster.pods:
    if now - pod.last_metric_time > STALE_THRESHOLD:
        mark_as_stale(pod)
        stop_routing_to_it()
```

Every request:
1. Check pod's last metric time
2. If > 5 minutes old → **STALE** → skip it
3. Route only to fresh pods

### Why This Matters

Without stale detection:
- Requests hit a silent, broken pod
- Timeout waiting for response
- User gets frustrated
- System looks slow

With stale detection:
- Request hits healthy pod immediately
- Response is fast
- System stays responsive

The rule: **Don't trust silence. If a pod hasn't reported in 5 minutes, it's dead.**

---

## Act 45: scale-decode-not-prefill - Specialized Scaling

This behavior tests: **"Never scale the wrong pod type."**

### The Test

```python
def behavior_scale_decode_not_prefill() -> BehaviorResult:
    """
    Scenario: Decode is saturated, prefill has space
    Expected: ONLY scale decode, don't touch prefill
    """
    prefill, decode, _ = _fleet(n_d=1)  # 1 decode, many prefill
    
    # Send requests that hit decode hard
    for i in range(20):
        resp = send(_req(i), Router(prefill, decode))
    
    # Planner should say: "Scale DECODE, leave prefill alone"
    # Should NOT say: "Scale prefill too"
```

### Why This Matters

```
GPU Memory Layout:
┌──────────────────────────────────┐
│ Prefill: 16GB (50% utilization)  │
│ Decode:  16GB (95% utilization)  │  ← Scale this!
│ Free:     8GB                     │
└──────────────────────────────────┘

❌ WRONG: Scale prefill (it has space but isn't the bottleneck)
✅ RIGHT: Scale decode (it's saturated)
```

The planner must:
1. Check prefill utilization
2. Check decode utilization
3. Only scale what's saturated
4. Never touch what's working

This saves costs: don't add prefill pods when you only need decode pods.

### In planner.py

```python
def plan(metrics):
    prefill_util = metrics['prefill_tokens'] / prefill_capacity
    decode_util = metrics['decode_tokens'] / decode_capacity
    
    if decode_util > 0.8 and prefill_util < 0.5:
        return "SCALE_DECODE_ONLY"  # Not prefill!
    
    if prefill_util > 0.8 and decode_util < 0.5:
        return "SCALE_PREFILL_ONLY"  # Not decode!
    
    if both > 0.8:
        return "SCALE_BOTH"
```

---

## Act 46: Monitoring Superlinked - Detecting Overflow

When your cluster is overwhelmed, requests overflow to Superlinked. Here's how to see it:

### Check 1: Superlinked Console (Real-time)
```
https://console.superlinked.com/console/usage
- Credit balance: $520
- Spend (30d): Increases when overflow happens
- Units metered: Shows API calls
```

**What to look for:**
- Spend changes from $0 → $X
- Units metered increase
- This means requests are hitting Superlinked

### Check 2: Lambda Logs
```bash
# SSH to Lambda:
make ssh

# Watch for overflow logs:
kubectl logs -f deployment/orch-serve | grep -i overflow

# You'll see:
# "Request 15: 503 → Overflow to Superlinked"
# "Superlinked response: 200 OK"
```

### Check 3: Local Traces
```bash
# On Mac, after sending requests:
tail -n 20 traces/requests.jsonl | jq '.[] | select(.via == "superlinked")'

# Shows all requests that went to Superlinked:
{
  "request_id": "req-7",
  "status": "503",
  "via": "superlinked",
  "model": "Qwen/Qwen3.5-4B",
  "latency_ms": 4200,
  "tokens_generated": 128
}
```

### When to Expect Overflow

Send requests to `make app`:

```
text Write about GPUs.        # Completes on cluster (local)
text Write about GPUs.        # Cluster full → 503 → Superlinked
text Write about GPUs.        # Still full → 503 → Superlinked
vision What color is this?    # Different model, might use cluster
audio Transcribe: hello       # Overflow if busy
```

Watch Superlinked console → should see **Spend increase** when overflow happens! 📈

---

---

## Act 47: abort-frees-kv - Cleanup on Cancellation

When a request is cancelled, don't waste decode resources on it.

```python
def behavior_abort_frees_kv() -> BehaviorResult:
    """
    Scenario: Request starts processing, then user cancels
    Expected: KV cache is freed, decode doesn't waste tokens
    """
    prefill, decode, kv_bus = _fleet()
    
    # Request starts
    resp = send(_req(0), Router(prefill, decode))
    
    # User cancels mid-processing
    resp.cancel()
    
    # Expected:
    # KV tokens allocated to this request are freed
    # Decode slot is released
    # Other requests can use them
```

**Why this matters:**
- Prevent wasted decode tokens on cancelled requests
- Free up KV memory quickly
- Other requests can reuse the slot

**In the code:**
```python
if request.cancelled:
    kv_bus.free(request.id)  # Release KV tokens
    decode.release_slot()     # Release decode slot
```

---

## Act 48: prefix-sticky-saves-kv - Reuse Cached Prefixes

When a prefix is already cached, route to that GPU to avoid recomputation.

```python
def behavior_prefix_sticky_saves_kv() -> BehaviorResult:
    """
    Scenario: Same prefix used by multiple requests
    Expected: Route to GPU with cached prefix, reuse KV
    """
    prefill, decode, kv_bus = _fleet()
    
    # Request 1: "Summarize this text: [large text]"
    # Prefill processes on GPU-A, caches KV
    resp1 = send(_req(0, prefix="Summarize this text:"), router)
    
    # Request 2: Same prefix, different question
    # Should route to GPU-A (prefix already cached)
    resp2 = send(_req(1, prefix="Summarize this text:"), router)
    
    # Expected:
    # Request 2 reuses cached prefix from Request 1
    # No need to recompute, just add new tokens
    # Saves prefill compute
```

**The Policy:**
```python
# "Sticky" means: stick to the GPU with cached prefix

if prefix_already_cached_on_gpu_A:
    route_to_GPU_A  # Reuse cache
else:
    route_to_least_loaded_GPU  # New computation
```

**Why this matters:**
- Prefix caching saves massive compute
- Example: Few-shot prompts with same examples
- Multiple requests can reuse the prefix

---

## Act 49: scale-both-pools - When Both Need Scaling

Sometimes prefill AND decode both need more capacity.

```python
def behavior_scale_both_pools() -> BehaviorResult:
    """
    Scenario: Both prefill AND decode are saturated
    Expected: Planner says "SCALE_BOTH"
    """
    prefill, decode, _ = _fleet(n_p=1, n_d=1)  # Each has 1 pod
    
    # Send requests that saturate BOTH
    for i in range(20):
        # Requests with large prefill + large decode
        resp = send(_req(
            i,
            prompt_tokens=100,    # Heavy prefill
            max_new_tokens=256    # Heavy decode
        ), router)
    
    # Expected:
    # Planner checks: "Both prefill and decode are > 80%"
    # Returns: "SCALE_BOTH"
    # Both pools scale up
```

**When does this happen?**
- Long context + long output (e.g., summarize 1000-word document → 500-word summary)
- High concurrency + complex requests
- Batch processing with large docs

**The decision:**
```python
if prefill_util > 0.8 and decode_util > 0.8:
    return "SCALE_BOTH"  # Add prefill AND decode pods
elif prefill_util > 0.8:
    return "SCALE_PREFILL_ONLY"
elif decode_util > 0.8:
    return "SCALE_DECODE_ONLY"
else:
    return "STABLE"
```

---

## Act 50: slice-oom-no-overflow - Memory Pressure Handling

What happens when KV cache fills up and can't be evicted?

```python
def behavior_slice_oom_no_overflow() -> BehaviorResult:
    """
    Scenario: KV memory full, can't evict enough tokens
    Expected: Instead of overflow, increase slice size
    """
    # GPU memory is sliced:
    # Prefill: 16GB
    # Decode: 16GB
    # Free: 8GB
    
    # Heavy prefill load fills entire prefill slice
    # Can't process more
    
    # Options:
    # 1. ❌ Overflow to Superlinked (slow)
    # 2. ✅ Increase prefill slice, shrink decode slice
    #       Prefill: 20GB, Decode: 12GB
    #       (if decode has headroom)
```

**Why "OOM but no overflow"?**
- Out of memory (OOM) in one slice
- But don't overflow to Superlinked
- Instead, dynamically resize GPU memory slices
- Rebalance based on demand

**Implementation (HAMI):**
```python
if prefill_kv_full and not can_evict:
    # Ask HAMI to resize slices
    hami.resize_slices(
        prefill_new=20,  # Increase
        decode_new=12    # Decrease
    )
```

This is why you need HAMI—GPU slice management!

---

## Summary: All Behaviors

| Behavior | Tests | File |
|----------|-------|------|
| fleet-soak | Concurrent load | router/overflow |
| unhealthy-decode-scales | Autoscaling | planner |
| tenant-429-stays | Error handling | gateway |
| ignore-stale-pod | Health detection | types |
| scale-decode-not-prefill | Specialized scaling | planner |
| abort-frees-kv | Request cancellation | kvbus |
| prefix-sticky-saves-kv | Cache reuse | router |
| scale-both-pools | Dual scaling | planner |
| slice-oom-no-overflow | Memory rebalancing | hami |
| overflow-on-503 | Fallback | overflow |

Each behavior tests a different aspect of your cluster:
- **Load handling:** fleet-soak
- **Resilience:** unhealthy, stale, OOM
- **Optimization:** prefix-sticky, scale-X
- **Fallback:** overflow-on-503

---

---

## Act 51: Request Slicing - Priority to Small Requests

When requests compete for limited resources, small requests get priority.

```python
def behavior_slice_priority() -> BehaviorResult:
    """
    Scenario: Big request and small request both waiting
    Expected: Small request succeeds, big request rejected
    """
    # Available KV: 1000 tokens
    
    # Big request: 800 tokens needed
    # Small request: 100 tokens needed
    
    # Both arrive simultaneously
    
    # Router decision:
    # "Can I fit both? 800+100 = 900 < 1000 ✓"
    # Process both
    
    # But if: Only 100 tokens free
    # "Can I fit both? 800+100 = 900 > 100 ✗"
    # Give priority to small (100 < 100 ✓)
    # Reject big (800 > 100 ✗)
```

**Why?**
- Small requests complete fast
- Keep system responsive
- Big requests can retry or queue

---

## Act 52: Aging & Admission - Preventing Request Starvation

Old requests get priority in admission layer (not router).

```python
# Admission layer (first stage)
if request.age > 60_seconds:
    return "PRIORITY"  # Old request gets in first

if request.age < 5_seconds:
    return "NORMAL"    # New request, normal priority
```

**Why split aging between layers?**

| Layer | Concern | Decision |
|-------|---------|----------|
| **Admission** | Fair queuing | Prioritize old requests so they don't starve |
| **Router** | Resource allocation | Don't look at age, just look at capacity |

Once a request is in the router, its age doesn't matter—only resources matter.

---

## Act 53: Behavior Aliases - Multiple Ways to Call Tests

The fakeworker supports both full names and short aliases:

```bash
# Full names:
python -m fakeworker.run --behavior fleet-soak
python -m fakeworker.run --behavior scale-decode-not-prefill
python -m fakeworker.run --behavior overflow-on-503

# Short aliases (same thing):
python -m fakeworker.run --behavior soak
python -m fakeworker.run --behavior scale-decode
python -m fakeworker.run --behavior overflow
```

Makes it faster to run tests repeatedly.

---

## Act 54: The Fakeworker Harness - Testing Gateway & Router

`fakeworker/run.py` is your **local test harness** for:
- ✅ Gateway admission logic
- ✅ Router routing logic
- ✅ KV management
- ✅ Overflow behavior
- ✅ Scaling decisions
- ✅ Error handling

**Before deploying to Lambda:**
1. Run all behaviors locally (fake GPU)
2. Verify logic is correct
3. **Then** deploy to real Lambda
4. Run smoke tests on real GPU

This saves time and money—find bugs before hitting expensive hardware!

---

## 🎉 Complete Class 9 Architecture

You now have:

### Documentation (50+ acts)
- Architecture & components
- Error handling & resilience  
- Autoscaling strategies
- Testing methodology
- Overflow fallback
- Memory management

### Working System
- ✅ Lambda cluster deployed (k3s + HAMI + KEDA)
- ✅ Disaggregated prefill/decode
- ✅ Mooncake KV store
- ✅ Gateway admission control
- ✅ Router with planner
- ✅ Overflow to Superlinked
- ✅ 10 different behavior tests
- ✅ Smoke tests passing

### Next Steps
1. ✅ Check Superlinked console for overflow traffic
2. Send traffic through `make app`
3. Watch traces in `traces/requests.jsonl`
4. See your cluster handle load, scale, and overflow!

---

---

## Act 55: Router is Generic - Fake or Real Doesn't Matter

Here's the key insight: **Your router/gateway code doesn't know if it's fake or real.**

```python
# router.py doesn't care:
async def route_request(request, workers):
    # "workers" could be:
    # - FakeWorkers (testing)
    # - Real vLLM pods (production)
    # As long as they respond to API calls, routing works!
    
    best_worker = select_best(workers)
    return await best_worker.process(request)
```

**Why?** Because:
- Gateway defines behavior (admission, queuing, metrics)
- Router defines policy (which pod, KV reuse, overflow)
- Both work with any AsyncEngine that responds to requests

**Testing strategy:**
```
┌─────────────────┐
│ Router/Gateway  │ (generic, mode-agnostic)
├─────────────────┤
│  FakeWorkers    │ (testing, deterministic)
│  Real vLLM      │ (production, complex)
└─────────────────┘
```

Same code. Different workers. That's the power of abstraction.

---

## Act 56: Black and White vs. Production Complexity

### Testing Phase (Fake GPU): Black and White ✓

```
IF   condition X happens
THEN behavior Y happens
ALWAYS (deterministic)
```

Example:
- "If KV is full, overflow to Superlinked" → Always happens
- "If request is 429, queue it" → Always happens
- "If pod is stale, ignore it" → Always happens

Everything is predictable. You can test all edge cases.

### Production Phase (Real GPU): Not Black and White ⚠️

```
IF   condition X happens
THEN behavior Y MIGHT happen
(unpredictable factors)
```

Example:
- "If KV is full, overflow" → But what if Superlinked is slow?
- "If pod is stale, ignore it" → But what if it's only slow, not broken?
- "If request times out..." → But timeout duration varies!

**Real-world factors:**
- Network latency varies
- GPU scheduling varies
- Request timing varies
- Cascading failures happen

**Solution:** Once fake testing passes:
1. Deploy to real cluster
2. Monitor in production
3. Handle unexpected behaviors
4. Iterate

This is why we test on fake first—to get the happy path right before dealing with chaos.

---

## Act 57: .env Configuration - Flexibility for Different Backends

Your `.env` is highly configurable. You can swap backends and models:

### Overflow Backends (choose one)

```bash
# Default: Superlinked
export OVERFLOW_BACKEND=superlinked
export OVERFLOW_BASE_URL=https://api.superlinked.com/v1
export OVERFLOW_API_KEY=sk-sie-...

# Alternative: OpenAI
export OVERFLOW_BACKEND=openai
export OVERFLOW_BASE_URL=https://api.openai.com/v1
export OVERFLOW_API_KEY=sk-...

# Alternative: Anthropic
export OVERFLOW_BACKEND=anthropic
export OVERFLOW_BASE_URL=https://api.anthropic.com/v1
export OVERFLOW_API_KEY=sk-ant-...

# Alternative: OpenRouter (handles multiple backends)
export OVERFLOW_BACKEND=openrouter
export OVERFLOW_BASE_URL=https://openrouter.ai/api/v1
export OVERFLOW_API_KEY=sk-or-...
```

OpenRouter is smart—it routes to the cheapest/fastest backend for you.

### Models (customize as you like)

```bash
# Today's models
export TEXT_MODEL=Qwen/Qwen2.5-3B-Instruct
export VISION_MODEL=Qwen/Qwen2.5-VL-3B-Instruct

# Try smaller models (cheaper GPU):
export TEXT_MODEL=meta-llama/Llama-2-7b-hf
export VISION_MODEL=openai/clip-vit-base-patch32

# Try even smaller (testing):
export TEXT_MODEL=TinyLlama/TinyLlama-1.1B
```

### Fixed (don't change for today)

```bash
export PREFILL_URLS=http://129.213.22.135:8000
export DECODE_URLS=http://129.213.22.135:8001
export MOONCAKE_URL=http://129.213.22.135:50051
```

The URLs must match your Lambda cluster endpoints.

---

## Act 58: Advanced Backend Selection with pick_backend.py

### The Problem with Static Routing

Right now, your router decides where to send requests based on:
- Pod health
- KV affinity
- Available capacity

But what if you wanted to make **intelligent cost-based decisions**? What if you wanted different requests to go to different backends based on their characteristics?

> "Instead of you defining those things manually, what it does, it automatically picks those things for you."

### The Solution: pick_backend.py

You can create a `pick_backend.py` file that acts as your **intelligent backend selector**. This file would:

1. **Analyze the request** - What model is needed? How many tokens?
2. **Make a cost decision** - Cheaper model? Expensive model? Fast vs. accurate?
3. **Select the backend** - Route to:
   - Your local vLLM pod (fast, but limited capacity)
   - Superlinked (overflow, but cheaper per token)
   - OpenRouter (multiple providers, auto-selection)
   - A specialized model provider (e.g., vision-only)

### Example Logic

```python
# pick_backend.py - Advanced routing decisions
def select_backend(request):
    # Example 1: Route vision requests to a vision model
    if request.type == "vision":
        return "vision-pod"
    
    # Example 2: Route expensive queries to overflow
    if request.tokens > 1000:
        return "overflow-superlinked"
    
    # Example 3: Route urgent requests to expensive fast model
    if request.priority == "high":
        return "fast-model"
    
    # Default: use local vLLM
    return "local-vllm"
```

### Where to Add It

You have two options:

**Option 1: Add to router.py (simplest)**
```python
# In router.py, add the pick_backend logic before overflow decisions
```

**Option 2: Create a separate module (cleaner)**
```
router/
  ├── router.py (main routing logic)
  ├── pick_backend.py (backend selection)
  └── overflow.py (overflow handling)
```

### Why This Matters

With `pick_backend.py`, you can:
- ✅ Route expensive queries to cheaper backends automatically
- ✅ Route specific model types to specialized hardware
- ✅ Create **agentic routing** (use an LLM to decide where to route!)
- ✅ A/B test different backends for the same request

> "You can add it simply in this part itself, or in a new file, and without changing up much of what you've done as it is now."

---

## Act 59: Lambda Setup Deep Dive - lambda_setup.sh

### What Happens When You Run lambda_setup.sh

This script runs **four critical checks** and installations. It's the foundation of your cluster.

#### 1. GPU Detection (nvidia-smi)

First thing: Does this instance even have a GPU?

```bash
# What this checks:
nvidia-smi  # Shows GPU name, memory, CUDA version
```

**Output you'll see:**
```
NVIDIA-SMI 535.104.05    Driver Version: 535.104.05
GPU Name: A100-SXM4-40GB
CUDA Version: 12.2
```

This tells you:
- ✅ GPU is present (if this fails, your instance is broken)
- ✅ GPU type (A100 = 40GB, you're slicing to 2x 16GB with HAMI)
- ✅ CUDA version (must match your vLLM build)

#### 2. Virtual Environment Setup

```bash
# Creates isolated Python environment
python3 -m venv ~/.venv
source ~/.venv/bin/activate
```

Why? So your pip installs don't pollute the system Python.

#### 3. pip Dependencies

```bash
# Installs from requirements.txt
pip install -r requirements.txt
```

This includes:
- FastAPI (gateway server)
- vLLM (the inference engine)
- Pydantic (configuration validation)
- Other utilities

#### 4. Torch Verification

```bash
# Verify PyTorch is correctly installed
python -c "import torch; print(torch.__version__)"
```

**Output you'll see:**
```
PyTorch 2.1.0
CUDA: 12.2
Device: NVIDIA A100-SXM4-40GB
```

This ensures:
- ✅ PyTorch installed correctly
- ✅ CUDA support is working
- ✅ GPU is detected by PyTorch

### Timing

**Expected runtime:** 3-5 minutes (mostly pip downloads)

### What Can Go Wrong

| Error | Cause | Fix |
|-------|-------|-----|
| `nvidia-smi: not found` | No GPU driver | Instance is misconfigured |
| `CUDA Version: None` | Driver issue | Restart instance, update driver |
| `torch: No module named` | pip install failed | Run `pip install torch` manually |

---

## Act 60: Lambda Cluster Deployment - lambda_cluster.sh

### The Complex Part: Why lambda_cluster.sh Takes 10 Minutes

This script **does the heavy lifting**. It installs Kubernetes, GPU slicing, and the cluster infrastructure.

> "This can be interesting, and the reason I say interesting is I have a time-out of 10 minutes for HAMI installs. Because there's a lot of things that have broken for me in the past."

### What Gets Installed (In Order)

#### 1. K3S (Kubernetes)
```bash
# Single-node Kubernetes cluster
k3s server
```

**What it does:**
- Starts a Kubernetes control plane
- Sets up container runtime
- Creates networking for pods
- Prints: "K3S is already installed" (if already exists)

**Why K3S?**
- Lightweight Kubernetes (smaller than full K8S)
- Designed for edge/single-node deployments
- Has built-in local storage

#### 2. Helm (Package Manager)
```bash
# Install Helm
helm repo add stable https://charts.helm.sh/stable
```

**What it does:**
- Sets up Kubernetes package manager
- Allows deploying complex apps via "charts"
- We use it for Mooncake and other components

#### 3. HAMI Installation (THE CRITICAL 10-MINUTE PART)

```bash
# Install GPU slicing
# This is where the timeout matters
```

**What HAMI does:**
- Detects your A100 GPU
- Creates virtual GPUs (vGPU) by slicing GPU memory
- Maps containers to specific vGPU allocations
- Configures port assignments for each vGPU

**Why this takes 10 minutes and is risky:**

```
[START HAMI INSTALL]
  ├─ Detect A100 GPU (2-3 sec)
  ├─ Allocate 16GB to vGPU-0 (3-5 sec)
  ├─ Allocate 16GB to vGPU-1 (3-5 sec)
  ├─ **Port assignment** (THIS IS THE TRICKY PART) ← can hang here
  │   - vGPU-0 gets :8001
  │   - vGPU-1 gets :8002
  │   - Mooncake gets :50051
  │   - Can fail if ports already in use
  │   - Can hit OOM during this phase
  ├─ Configuration sync (2-3 sec)
  └─ Verify setup (1-2 sec)
[DONE]
```

### ⚠️ CRITICAL: Don't Ctrl+C During HAMI Install

```bash
bash setup/lambda_cluster.sh
# DO NOT PRESS CTRL+C
# Even if it looks stuck, wait the full 10 minutes
# Ctrl+C leaves vGPUs in broken state
```

**Why?**
- Partial vGPU allocation can't be undone cleanly
- Ports might be stuck "in use"
- Next run will fail with "Address already in use"
- Recovery requires manual cleanup (kill processes, reset network)

### Common Issues During HAMI

| Issue | Cause | Fix |
|-------|-------|-----|
| Hangs at "Port assignment" | Network issue or OOM | Wait 10 min, if still hangs: `pkill -f hami` |
| "Address already in use" | Previous run didn't clean up | `lsof -i :8001` then `kill -9 <pid>` |
| "Out of memory" during vGPU alloc | Pod using too much RAM | Check with `free -h`, restart instance if <2GB |
| HAMI fails after 10 min | Permanent failure | Check logs: `journalctl -u hami -f` |

### After HAMI Install

Once `lambda_cluster.sh` completes, you should see:

```bash
kubectl get pods
# Output should show:
# - vllm-prefill-0     (on vGPU-0)
# - vllm-decode-0      (on vGPU-1)
# - mooncake-0         (KV store)
# - gateway            (your request handler)
```

---

## Act 61: Customizing for Different GPUs

### If You're Using a Smaller GPU (16GB)

The default setup assumes an A100 (40GB) sliced into two 16GB pieces.

**If you have:**
- A10 (24GB) → Slice into 12GB + 12GB
- RTX 3090 (24GB) → Slice into 12GB + 12GB
- RTX 4090 (24GB) → Slice into 12GB + 12GB
- V100 (16GB) → Can't slice, use single GPU

**To customize:**

Edit `setup/lambda_cluster.sh` and look for:
```bash
# Find the HAMI configuration section
--vgpu-memory=16000  # Change this to your GPU memory / 2
```

Or edit `k8s-config/hami/` YAML files:
```yaml
resources:
  limits:
    nvidia.com/gpu: 1          # Still requests 1 physical GPU
    nvidia.com/vgpu: 16000     # But allocates 16GB virtual
```

**Test before deploying:**
```bash
# On Lambda, run:
nvidia-smi  # Check your GPU memory
# Then adjust HAMI config
bash setup/lambda_cluster.sh
```

---

## Act 62: What HAMI Really Does (The Technical Details)

### GPU Slicing 101

**Before HAMI (standard setup):**
```
Application 1 → A100 (40GB) ← single task monopolizes entire GPU
```

**After HAMI (disaggregated):**
```
Prefill task  → vGPU-0 (16GB) ─┐
Decode task   → vGPU-1 (16GB) ─┤ Same physical A100
Metadata      → system memory  ─┘
```

### How HAMI Enforces This Isolation

1. **Memory isolation:** Each vGPU gets a separate memory pool
   - vGPU-0: 0-16GB of A100
   - vGPU-1: 16-32GB of A100

2. **Port isolation:** Each vGPU gets separate ports
   - vGPU-0: Prefill server on :8000
   - vGPU-1: Decode server on :8001

3. **Process isolation:** NVIDIA Container Runtime enforces which process uses which vGPU

### What Your Router Sees

```python
# In router.py, after HAMI setup:
PREFILL_URLS = ["http://129.213.22.135:8000"]  # vGPU-0
DECODE_URLS = ["http://129.213.22.135:8001"]   # vGPU-1

# Router sends requests like:
# Step 1: Prefill on port 8000
curl http://129.213.22.135:8000/prefill_step
# Step 2: Decode on port 8001 (with KV from step 1)
curl http://129.213.22.135:8001/decode_step
```

### Why Disaggregation Matters

**Without disaggregation:**
- 1 request uses entire A100 for entire duration
- Capacity: 1 request at a time

**With disaggregation (HAMI):**
- Prefill (fast, memory-intensive) on optimized hardware
- Decode (slow, compute-intensive) on cheaper hardware
- Capacity: 4-8 concurrent requests possible

---

## Act 63: HAMI vs Router - Clear Separation of Concerns

### The Confusion Point

Many people think HAMI and the Router do the same thing. They don't.

> "How big is this replica going to be? Which part will get the request? That part is not really handled by Hammy. That part is still handled by a router."

### What HAMI Does (Resource Allocation)

HAMI is responsible for **"how"**:
- ✅ How much GPU memory does each vGPU get?
- ✅ How many GPU cores are allocated?
- ✅ How are physical resources sliced?
- ✅ Which port does each vGPU use?

**HAMI doesn't care about:** Which request goes where

### What Router Does (Request Routing)

Router is your **control plane** responsible for **"which"**:
- ✅ Which request goes to which pod?
- ✅ Which pod has the best KV affinity?
- ✅ Is pod-1 healthier than pod-2?
- ✅ Do we overflow to Superlinked?

**Router doesn't care about:** GPU memory allocation

### The Architecture Separation

```
┌─────────────────────────────────────────┐
│ YOUR SYSTEM                             │
├─────────────────────────────────────────┤
│                                         │
│ GATEWAY (Admission Control)             │
│    ↓                                    │
│ ROUTER (Which pod? Where to send?)      │
│    ↓                                    │
│ [HAMI: GPU slicing happens here]        │
│    ├─ vGPU-0 (Prefill, 16GB)           │
│    └─ vGPU-1 (Decode, 16GB)            │
│    ↓                                    │
│ vLLM PODS (Process request)             │
│                                         │
└─────────────────────────────────────────┘

HAMI = "How much resources?"
Router = "Which pod gets the request?"
```

### Why This Separation Matters

If you wanted to **change GPU slicing** (e.g., 25%/75% instead of 50%/50%):
- Edit HAMI config only
- Router code doesn't change

If you wanted to **change routing strategy** (e.g., prefer decodes, avoid prefills):
- Edit router.py only
- HAMI config doesn't change

**Clean separation = easy to modify without breaking everything**

---

## Act 64: KEDA - The Autoscaling Brain

### What KEDA Does

KEDA stands for "Kubernetes Event-Driven Autoscaling." It's your cluster's **autopilot** for scaling.

> "Keda for basically for like counting and managing of the GPU ports."

### KEDA's Four Jobs

#### 1. Metric Collection
```bash
# KEDA watches vLLM metrics
# How many active requests per pod?
# How much KV memory in use?
# What's the latency?
```

#### 2. Replica Counting
```bash
# KEDA counts how many vLLM pods exist
kubectl get pods  # Shows current count
# KEDA notices this number
```

#### 3. Auto-scaling Decision
```bash
# KEDA logic:
if active_requests > threshold:
    scale_up()  # Create new pod
elif active_requests < low_threshold:
    scale_down()  # Delete unused pod
```

#### 4. GPU Port Management
```bash
# KEDA coordinates with HAMI
# When scaling up:
# 1. HAMI allocates new vGPU
# 2. KEDA assigns new port (e.g., :8002, :8003)
# 3. Router is notified of new pod
```

### KEDA Configuration (Your Setup)

In `k8s-config/keda/scaledobject.yaml`:

```yaml
triggers:
  - type: prometheus  # Watch Prometheus metrics
    metadata:
      query: vllm_active_requests  # Metric to watch
      threshold: '10'              # Scale up at 10 requests
      activationThreshold: '5'     # Scale down at 5 requests
```

### KEDA in Action

```
Time 0:00 → 1 pod running
           ↓
Time 0:15 → Requests arrive (12 active)
           ↓
Time 0:20 → KEDA detects: 12 > 10 threshold
           ↓
Time 0:25 → New pod created: pod-2
           ↓
Time 0:30 → 2 pods running, requests balanced
```

### Why KEDA Matters

Without KEDA:
- You manually scale: `kubectl scale --replicas=5`
- You have to watch metrics yourself
- Capacity planning is guesswork

With KEDA:
- Automatic scaling based on load
- Responds to real metrics
- Can scale down when idle (save $$$)

---

## Act 65: Essential kubectl Commands for Operations

### The Most Important Commands

#### 1. See Your Pods (Most Important!)

```bash
# List all pods and their status
kubectl get pods

# Output:
# NAME              READY   STATUS    RESTARTS
# vllm-prefill-0    1/1     Running   0
# vllm-decode-0     1/1     Running   0
# mooncake-0        1/1     Running   0
# gateway-xyz       1/1     Running   0

# Watch pods in real-time (auto-updates)
kubectl get pods -w

# See detailed pod info
kubectl describe pod vllm-prefill-0
```

**What to look for:**
- ✅ STATUS = "Running" (healthy)
- ⚠️ STATUS = "Pending" (waiting for resources)
- ❌ STATUS = "CrashLoopBackOff" (pod crashed repeatedly)

#### 2. Check Deployments and Scaling

```bash
# See all deployments and replica counts
kubectl get deployments

# Output:
# NAME           READY   UP-TO-DATE   AVAILABLE
# vllm-prefill   2/2     2            2
# vllm-decode    3/3     3            3

# See autoscaling status
kubectl get scaledobject
```

#### 3. View Logs (Debugging)

```bash
# See logs from a pod
kubectl logs vllm-prefill-0

# Follow logs in real-time
kubectl logs -f vllm-prefill-0

# See logs from all replicas
kubectl logs -l app=vllm-prefill
```

**Common errors to look for:**
- `CUDA out of memory` → Pod allocated too little GPU
- `Connection refused` → Port issues (HAMI config problem)
- `ModuleNotFoundError` → Python dependencies missing

#### 4. Delete Stale Pods (The Cleanup Command)

```bash
# Delete a specific pod (it restarts automatically)
kubectl delete pod vllm-prefill-0

# Why do this?
# - Pod is stuck (not responding)
# - Previous run left stale state
# - HAMI failed, port is stuck
# - You need a clean slate

# Delete all pods in a deployment
kubectl delete pods -l app=vllm-prefill

# Force delete a stuck pod
kubectl delete pod vllm-prefill-0 --grace-period=0 --force
```

### Recovery: When HAMI Messed Up

Sometimes HAMI installation fails midway:

```bash
# Symptom: Pods won't start, port conflicts
# Step 1: Delete all problematic pods
kubectl delete pods --all

# Step 2: Check if ports are truly freed
lsof -i :8000
lsof -i :8001
lsof -i :50051

# Step 3: If ports are still bound, kill the processes
kill -9 <PID>

# Step 4: Restart cluster
bash setup/lambda_cluster.sh
```

### Useful Monitoring Commands

```bash
# See all resources (pods, services, deployments, scaled objects)
kubectl get all

# Watch autoscaling in action
watch 'kubectl get scaledobject'

# See if any pod is using too much CPU/memory
kubectl top pods

# Get all events (see what's happening)
kubectl get events --sort-by='.lastTimestamp'
```

---

## Act 66: GPU Slicing Strategies - Beyond 50/50

### Standard Setup: 50/50 Split

Your default setup:
```
A100 (40GB)
├─ vGPU-0 (Prefill): 20GB  (50%)
├─ vGPU-1 (Decode):  20GB  (50%)
└─ System:           reserved
```

**Why 50/50?**
- Balanced for typical workloads
- Prefill is memory-hungry (benefits from 20GB)
- Decode is compute-bound (20GB is plenty)

### Alternative Strategies

#### Strategy 1: 25/75 (More Decode)

```
A100 (40GB)
├─ vGPU-0 (Prefill): 10GB  (25%)
└─ vGPU-1 (Decode):  30GB  (75%)
```

**When to use:**
- Many concurrent decoding tasks
- Prefill is fast, decode is your bottleneck
- Example: Long-running generations (code, stories)

#### Strategy 2: 75/25 (More Prefill)

```
A100 (40GB)
├─ vGPU-0 (Prefill): 30GB  (75%)
└─ vGPU-1 (Decode):  10GB  (25%)
```

**When to use:**
- Many short prefix tasks
- Prefill is the bottleneck
- Example: Summarization (lots of input, little output)

#### Strategy 3: Multi-GPU (No Slicing)

```
GPU-0: Prefill (40GB A100)
GPU-1: Decode  (40GB A100)
```

**When to use:**
- You have multiple physical GPUs
- Want maximum isolation
- No HAMI overhead

#### Strategy 4: Three-way Split (Advanced)

```
A100 (40GB)
├─ vGPU-0 (Prefill):     15GB (37%)
├─ vGPU-1 (Decode-1):    15GB (37%)
└─ vGPU-2 (Decode-2):    10GB (26%)
```

**When to use:**
- Very high concurrent decoding
- Can scale decode independently

### How to Change Slicing

Edit `setup/lambda_cluster.sh`:

```bash
# Find the HAMI configuration section
# Look for lines like:
--mem-percentage=50,50  # Change to your split

# Example: Change to 25/75
--mem-percentage=25,75

# Then restart
bash setup/lambda_cluster.sh
```

Or edit Kubernetes YAML directly:

```yaml
# In k8s-config/hami/vgpu-config.yaml
vgpus:
  - name: prefill
    memory: 10000    # 10GB
  - name: decode
    memory: 30000    # 30GB
```

### Monitoring Your Slicing

After setup, check actual allocation:

```bash
# On Lambda, run:
nvidia-smi

# Output shows:
# GPU 0: A100-SXM4-40GB
#   vGPU-0: 20GB allocated
#   vGPU-1: 20GB allocated
```

### When to Re-slice

**Re-slice if:**
- Prefill pods are **constantly full** (50% utilization)
- Decode pods are **idle** (10% utilization)
- You're getting OOM errors on one side but not the other

**Don't re-slice if:**
- Both sides are balanced
- Overflow is handling overflow well
- System meets your performance goals

---

## Act 67: Deployment Flow and Timeouts - What Actually Happens

### The Deployment Sequence

When you run `bash setup/lambda_cluster.sh`, this is what happens step-by-step:

#### Step 1: GPU Detection (30 seconds)
```bash
nvidia-smi
# Output shows: A100-SXM4-40GB, CUDA version, memory
```

#### Step 2: HAMI Installation (~10 minutes) ⚠️
```bash
# Downloading HAMI
# Allocating vGPU-0: 16.3GB (for prefill or text)
# Allocating vGPU-1: 16.3GB (for decode or vision)
# Creating port mappings (:8000, :8001)
# **CRITICAL: Don't interrupt this step**
```

> "Initially I did 50% slicing on both the GPUs... out of these 40 gigabytes, create me two slices of like 16.3 megabytes each"

**If it hangs during HAMI:**
```bash
# Wait the full 10 minutes
# If still hangs after 10 min:
pkill -f hami
# Then restart
bash setup/lambda_cluster.sh
```

#### Step 3: KEDA Installation (2-3 minutes)
```bash
# Installing Kubernetes Event-Driven Autoscaling
# Configures metric collection
# Sets up replica management
```

**If KEDA times out:**

> "If it times out then you'll have to manually install KEDA. So, let me know and I'll give you the commands for that one."

```bash
# Manual KEDA install (if auto-install fails)
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda --namespace keda --create-namespace
```

#### Step 4: Mooncake KV Store (3-5 minutes) ⏱️
```bash
# Deploying distributed KV cache
# Creating gRPC endpoints
# Verifying connectivity
```

> "Moonkick technically should take somewhere between 3 to 5 minutes, but if it goes over 5 minutes, then you are like, okay, there's something really happening, which is probably you've OOMed"

**If Mooncake takes >5 minutes:**
- Likely **Out of Memory** error
- Check instance resources: `free -h`
- May need to restart Lambda instance

---

## Act 68: The Critical kubectl Command and What It Shows

### The Magic Command

```bash
kubectl get deploy,svc,scaledobject
```

This is your **deployment health dashboard**. Run this after cluster deployment.

### What You Should See

```
NAME                           READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/mooncake       1/1     1            1           2m
deployment.apps/vllm-decode    2/2     2            2           1m
deployment.apps/vllm-prefill   1/1     1            1           1m

NAME                    TYPE        CLUSTER-IP       PORT(S)
service/mooncake        ClusterIP   10.43.201.100    50051/TCP
service/orchestration   ClusterIP   10.43.102.50     8080/TCP
service/vllm-decode     ClusterIP   10.43.150.200    8001/TCP
service/vllm-prefill    ClusterIP   10.43.99.50      8000/TCP

NAME                              SCALETARGETKIND     MIN   MAX
scaledobject.keda.sh/vllm-decode  Deployment/vllm     1     4
```

### Understanding Each Column

| Column | Means | What to Look For |
|--------|-------|------------------|
| **READY** | Pods running / Total pods | Should be X/X (e.g., 1/1) |
| **UP-TO-DATE** | Pods with latest version | Should match READY |
| **AVAILABLE** | Pods actually serving traffic | Should match READY |
| **AGE** | How long pod has been running | Recent (just deployed) |

### Port Mapping (Critical!)

```
Service               Port    What It Does
─────────────────────────────────────────────
vllm-prefill          8000    Input token processing
vllm-decode           8001    Output token generation
orchestration (router) 8080    Request routing decisions
mooncake (KV store)   50051   Distributed token cache
gateway               8080    (same as orchestration)
```

### What If It Prints Nothing?

```bash
kubectl get deploy,svc,scaledobject
# Returns: No resources found in default namespace
```

**This means:** Something failed during installation. Debugging needed:

```bash
# Check what actually exists
kubectl get all

# Check for errors
kubectl get events --sort-by='.lastTimestamp'

# Check logs
kubectl logs -l app=vllm-prefill
kubectl logs -l app=vllm-decode
kubectl logs -l app=mooncake
```

---

## Act 69: Common Deployment Errors and Debugging

### Error 1: "Unhandled error: couldn't get server API"

```
Error: unhandled error couldn't get server API
```

**Cause:**
> "There's a very good chance your prefill or your decode endpoints are not matching"

**Debugging:**

```bash
# SSH into Lambda in a NEW terminal
ssh -i ~/.ssh/lambda_instance ubuntu@129.213.22.135

# Check if services are actually running
kubectl get svc

# Verify prefill is on 8000
curl http://127.0.0.1:8000/health

# Verify decode is on 8001
curl http://127.0.0.1:8001/health

# If one fails, check its pod logs
kubectl logs deployment/vllm-prefill
kubectl logs deployment/vllm-decode
```

### Error 2: "Only point two printed" / Incomplete Output

```bash
kubectl get deploy,svc,scaledobject
# Output: deployment.apps/point.two (incomplete)
```

**Cause:**
> "That means some something went wrong. Your pods are not set up or they are not warmed up"

**Debugging:**

```bash
# Check pod status
kubectl get pods

# If a pod shows "Pending" or "CrashLoopBackOff":
kubectl describe pod vllm-prefill-0

# Check resource requests vs available
kubectl describe node

# Common issue: Not enough memory
# Solution: Restart instance or reduce replica count
kubectl scale deployment vllm-prefill --replicas=1
```

### Error 3: Mooncake Deployment Stuck (>5 minutes)

```bash
# Pod stuck in "Pending" state
kubectl get pods | grep mooncake
# Output: mooncake-0  0/1  Pending  0  10m
```

**Cause:**
> "Probably you've OOMed or something else"

**Debugging:**

```bash
# Check node memory
kubectl top nodes
free -h

# Check pod logs
kubectl logs deployment/mooncake

# If really stuck, delete and restart
kubectl delete pod mooncake-0
# Then wait for auto-restart
kubectl get pods -w
```

### Error 4: Port Already in Use

```
Error: Address already in use: :8000
```

**Cause:** Previous deployment didn't clean up

**Debugging:**

```bash
# Find what's using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>

# Verify it's free
lsof -i :8000
# (should return nothing)

# Try deployment again
bash setup/lambda_cluster.sh
```

### Error 5: Service Can't Reach Endpoint

```bash
# Service exists but endpoint is empty
kubectl get endpoints

# Should show:
# orchestration     10.42.0.5:8080
# vllm-decode       10.42.0.6:8001
```

**If empty:**

```bash
# Check if pod is actually running
kubectl get pods -o wide

# If pod is "NotReady", check why
kubectl describe pod <pod-name>

# Common: Container failed to start
# Check logs:
kubectl logs <pod-name>
```

---

## Act 70: Don't Debug in the Same Terminal - The Golden Rule

### The Rule

> "Don't do this on the same SSH or where you're trying to run your Hami"

### Why?

When you're running `bash setup/lambda_cluster.sh`, that terminal is **busy with setup**. If you try to run debugging commands in the same terminal:

1. Setup script gets interrupted
2. HAMI partial installation left in broken state
3. Ports get stuck "in use"
4. Recovery becomes very hard

### The Right Way

**Terminal 1:** Run setup
```bash
# Terminal 1 (Keep this running!)
ssh -i ~/.ssh/lambda_instance ubuntu@129.213.22.135
cd ~/class9
bash setup/lambda_cluster.sh
# Just watch and wait... don't interrupt!
```

**Terminal 2:** Debug separately
```bash
# Terminal 2 (Open a NEW Mac terminal)
ssh -i ~/.ssh/lambda_instance ubuntu@129.213.22.135
# Now run your debugging commands here
kubectl get pods
kubectl get events
# etc.
```

### Debugging While Setup Runs

If setup is taking too long:

```bash
# In Terminal 2, check progress:
kubectl get pods -w  # Watch pods appear

# See what's happening:
kubectl get events --sort-by='.lastTimestamp'

# Check specific pod logs:
kubectl logs -f deployment/mooncake
```

### When Setup Completes

In Terminal 2:

```bash
# Verify everything came up
kubectl get deploy,svc,scaledobject

# Test connectivity
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:50051/health  # Mooncake gRPC

# Check the router
curl http://127.0.0.1:8080/status
```

### Recovery Checklist

If deployment failed, use this checklist:

- [ ] Check instance has enough memory: `free -h`
- [ ] Verify GPU is present: `nvidia-smi`
- [ ] Check all pods: `kubectl get pods`
- [ ] See errors: `kubectl get events`
- [ ] Check specific pod: `kubectl describe pod <name>`
- [ ] Review logs: `kubectl logs <pod-name>`
- [ ] Free stuck ports: `lsof -i :<port>` then `kill -9 <pid>`
- [ ] Delete broken pod: `kubectl delete pod <name>` (auto-restarts)
- [ ] Retry deployment: `bash setup/lambda_cluster.sh`

---

## Act 71: Production Alternatives — The Map by Plane

### Real-World Tooling Landscape

After building Class 9 from first principles, here's what production teams actually use:

#### Northbound (Your Router)
- **Superlinked** (what we use)
- **OpenAI/Anthropic direct**
- **Bedrock/Vortex**
- **OpenRouter**
- **LiteLLM proxy** (abstraction layer)
- **Portkey** (routing + observability)

#### Gateway + Routing
- **GIE EPP** (Google's approach, Envoy-based)
- **K-Gateway / AgentGateway** (similar to our implementation)
- **llm-d** (LLM production stack)
- **NVIDIA Dynamo Router**
- **AiBrix**
- **Ray Serve LLM**
- **KServe** (Kubernetes-native)

#### KV Transfer + Cache
- **Mooncake** (what we use - distributed KV store)
- **LMCache** (alternative KV caching)
- **NXKL / RDMA / NVLink** (hardware-level transfers)
- **In-engine API only** (no external transfer)

#### Device Plane (GPU Slicing)
- **HAMI** (what we use)
- **NVIDIA MIG** (hardware GPU partitioning)
- **Time-slicing** (simple scheduling)
- **MPS** (Multi-Process Service)
- **KAI Scheduler** (advanced scheduling)
- **Kubernetes DRA** (new Kubernetes feature)

#### Scaling Plane
- **KEDA** (what we use - event-driven autoscaling)
- **Dynamo Planner** (intelligent capacity planning)
- **Kubernetes HPA** (basic horizontal autoscaling)
- **Knative** (serverless scaling)

### The Transition Path

**Stage 1: First Principles (Where You Are)**
- Custom gateway (like app.py)
- Custom router (like router.py)
- Manual Kubernetes management
- Single overflow backend

**Stage 2: Tooling Integration**
- Keep your router, use KServe for gateway
- Use LiteLLM to abstract multiple backends
- Use KEDA for autoscaling

**Stage 3: Full Stack**
- Use vLLM for serving
- Use Dynamo for routing
- Use Mooncake for KV
- Use Bedrock/OpenAI for overflow

### Tool Interchangeability

**The beauty of Class 9:** You can swap components easily:

| Component | Current | Alternative 1 | Alternative 2 |
|-----------|---------|---------------|-|
| **Router** | Custom (router.py) | LiteLLM | Dynamo |
| **Gateway** | Custom EPP | Envoy | K-Gateway |
| **KV Store** | Mooncake | LMCache | In-engine API |
| **Device Plane** | HAMI | NVIDIA MIG | Time-slicing |
| **Scaling** | KEDA | Dynamo Planner | K Native |

**Change any component without rewriting the whole system!**

### Real-World Production

> "At OpenAI and Anthropic, they still use K8s as base infrastructure. Then they add custom routers, custom gateways, and custom extensions exactly like what you built."

**The pattern:**
1. Start with generic tool (KServe, Ray Serve)
2. Add custom extensions for your use case
3. Eventually replace entire tool if needed

**Or go full custom** (like you did):
1. Build from first principles
2. Understand every line
3. Add tooling as needed

### Workload-Specific Choices

**Different workloads optimize for different tools:**
- **Agentic workloads** → Different tool preferences
- **Batch inference** → Different optimization
- **Real-time streaming** → Different requirements
- **Multi-model serving** → Different architecture

### Key Insight

> "Most deployments start exactly like Class 9 — from first principles. As complexity grows, teams adopt tooling. But the underlying concepts remain the same."

**At OpenAI/Anthropic:** K8s infrastructure + custom routers + custom gates = **exactly like what you built**

This is **production-grade infrastructure**. The only missing piece is **observability** (monitoring, tracing, dashboards) — coming tomorrow!

---

## 🎓 Complete Class 9 Journey

You've learned:

1. **Architecture** (Acts 1-10): Gateway, router, KV, overflow
2. **Components** (Acts 11-24): HAMI, Mooncake, KEDA, setup
3. **Testing** (Acts 25-54): Fake before real, all 10 behaviors
4. **Philosophy** (Acts 55-57): Generic code, black vs. white, flexibility

### What You Have Now

✅ **Fake GPU testing** (fakeworker) — all behaviors pass  
✅ **Real Lambda cluster** — k3s, vLLM, pods running  
✅ **Gateway on Lambda** — listening, routing traffic  
✅ **Overflow to Superlinked** — configured and ready  
✅ **Documentation** — 57 acts for studying  

### What's Next

🚀 **Send real traffic** through the gateway  
📊 **See overflow trigger** Superlinked API calls  
📈 **Watch metrics** in traces/requests.jsonl  
🎯 **Test edge cases** with concurrent load  

---

## Putting It All Together: The Full Flow

```
User sends request
    ↓
[GATEWAY - Admission]
  "Are we within tokens/sec limit?" 
  If no: reject or queue
    ↓
[QUEUE]
  "Wait here if needed"
    ↓
[ROUTER - Type Handling]
  "Which pod is healthiest?"
    ↓
[ROUTER - KV Decision]
  "Can we reuse tokens from pod-2?"
  If yes: transfer KV
  If no: start fresh
    ↓
[ROUTER - Overflow Check]
  "Do we have space?"
  If no: send to overflow
    ↓
[vLLM POD]
  Generate response
    ↓
[METRICS]
  Track: tokens, rejection rate, KV transfers
    ↓
Response back to user
```

---

## Why This Architecture?

### Problem 1: Scaling Beyond One GPU
- **Solution:** The router decides which GPU gets the request

### Problem 2: Running Out of Memory
- **Solution:** The KV bus tracks and moves tokens; overflow handles overflow

### Problem 3: Knowing What's Actually Happening
- **Solution:** Custom metrics dashboard for cluster health

### Problem 4: Rejecting Bad Requests Early
- **Solution:** Gateway admission before expensive queueing

---

## Your Learning Path

### Phase 1: Understand the Fake Worker (Steps 6-9)
Run different failure scenarios locally. See how the router responds.

### Phase 2: Deploy the Real System (Steps 10-15)
Get k3s running. Deploy actual vLLM pods. Watch them communicate.

### Phase 3: Send Traffic (Steps 16-25)
Send real requests. Watch the dashboard. See the metrics flow.

### Phase 4: Break It Intentionally
Stop a pod. Fill up KV memory. Send a ton of requests. See what the system does.

---

## Key Takeaways

1. **Fake before real** - Test admission/routing on fake workers first
2. **Measure what matters** - Standard metrics aren't enough for clusters
3. **Health is continuous** - One bad metric doesn't mean it's broken, but consistent silence does
4. **Graceful degradation** - Overflow when full; don't just fail
5. **Configuration is crucial** - Different deployments need different thresholds

---

## Next Steps

1. Open a terminal and `cd class9`
2. Run `make ssh` to connect to your Lambda instance
3. Run `bash setup/lambda_setup.sh` to install k3s
4. Run `bash setup/lambda_cluster.sh` to deploy the cluster
5. Watch the system come alive with `kubectl get pods -w`

Good luck! 🚀
