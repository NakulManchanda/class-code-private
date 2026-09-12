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
