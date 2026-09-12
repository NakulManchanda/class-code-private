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
