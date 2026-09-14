# Class 9b — Key Concepts & Terminology

**From Instructor Revision Slides**

---

## The Six Tools

### 🔷 **HAMi** — GPU Sharing Layer for Kubernetes

**What it does:**
- Answers: "How much GPU will this pod see?"
- Hands a pod a hard slice of one card: memory (gpumem) + compute (gpucores)
- Enforces the slice via CUDA call interception

**What it is NOT:**
- ❌ Not a router (doesn't decide "which pod gets this request")
- ❌ Never reasons about admission or routing

**Key point:** HAMi is purely about **GPU resource allocation**, not request routing.

---

### ⚙️ **KEDA** — Kubernetes Event-Driven Autoscaler

**What it does:**
- Reads a metric from Prometheus
- Changes the replica count of ONE Deployment
- Operates on a timescale of tens of seconds to minutes

**What it is NOT:**
- ❌ Not per-request (doesn't scale on individual requests)
- ❌ Cannot change multiple deployments at once
- ❌ Cannot anticipate load (reactive only, not predictive)

**Key point:** KEDA is your **reactive scaling engine**. Planner.py in the router is the predictive part.

---

### 💾 **KV Cache** — Cached Attention State

**What it is:**
- The attention Keys and Values already computed for tokens in a sequence
- Lives in GPU memory and grows as sequence grows
- Discarded Q values (not needed for next computation)

**Why it matters:**
- Avoids recomputing the same attention for the same tokens
- Huge speedup for decode phase (no need to recompute prefix)

**What it is NOT:**
- ❌ Not a response cache (not about repeated answers)
- ❌ Not about caching model weights
- ❌ Activations don't cross GPUs (stay in SRAM on the compute GPU)

**Key point:** KV cache saves compute by reusing pre-computed attention state.

---

### 🏪 **Mooncake** — KV Transfer Engine

**What it is:**
- A KV store + transfer engine
- A place to **park cached attention state** so different pods can pick up the sequence
- Defines: eviction policies, which pods can access which stores, prefill/decode coordination

**When you need it:**
- ✅ When you split prefill and decode across different pods
- ❌ Not needed if prefill and decode are on same pod

**What it is NOT:**
- ❌ Not just a store (includes transfer logic and policies)
- ❌ Doesn't do KV-aware routing (LM-cache does that)

**Key point:** Mooncake enables **KV hops** between prefill and decode pods.

---

### 📡 **SSE** — Server-Sent Events

**What it is:**
- Streaming format behind `stream: true`
- A sequence of chunks ending in `[DONE]`
- Streaming transport for LLM responses

**What it is NOT:**
- ❌ Not a WebSocket (different protocol)
- ❌ Not a guarantee that generation was slow (just the streaming format)

**Key point:** SSE is how streaming LLM responses are transmitted.

---

### 📊 **Locust** — Load Generator

**What it does:**
- Points at your gateway
- Specifies users, ramp rate, and sends requests
- Receives a wall of response codes back

**What it measures:**
- ✅ Your admission policy behavior
- ✅ Gateway performance under load
- ✅ Request rejection rates

**What it is NOT:**
- ❌ Not a benchmark of the model (measures **your system**, not model quality)
- ❌ Not a benchmark of inference speed (measures **admission control**, not model speed)

**Key point:** Locust benchmarks **your orchestration system**, not the model.

---

## Important Ratios & Heuristics

### Prefill : Decode Pod Ratio

**For MHA models:**
- Ratio: **1:1** (same number of prefill and decode pods)

**For MQE models:**
- Ratio: **1:2 or higher** (more decode pods than prefill)
- Based on: How many heads are shared across attention layers
- If 4 layers share one head → 1:4 ratio is reasonable

**Note:** This is a heuristic, not proven. Adjust based on your workload.

---

### GPU Memory Allocation (40GB Machine)

**With split=capability:**
- Text model: ~15GB per replica (2 replicas total)
- Model size: ~6-7GB
- KV cache overhead: ~8GB per concurrent request

**Safe concurrency:** 5-10 users  
**Max before heavy shedding:** 10-20 users  
**Expected shedding:** 30-50% at capacity

---

### Platform Stress Test Results (Lambda vs Others)

From instructor's stress testing:

| Platform | Rejection Rate | Notes |
|----------|-----------------|-------|
| **Lambda** | 18-20% | Capacity available, platform not robust enough |
| **Modal** | High (variable) | Serverless, cold-start issues for batch testing |
| **Vorta** | <2% | Strong platform, but limited GPU capacity |
| **N-scale** | Good | Reasonably good queue depth handling |

**Key insight:** Different platforms optimize for different things. Lambda is easy to use but has queue depth limitations.

---

## Architecture Components

### EPP (Endpoint Picker) — The Brain

**What it does:**
- Answers: "Which endpoint should serve this request?"
- Filters candidates by eligibility
- Decides if request should be shed

**Location:** Can be in gateway layer or Kubernetes container

**Key point:** EPP is the **orchestration brain**. It chooses among available capacity but cannot create it.

---

### Inference Pool

**What it is:**
- A Kubernetes object (not a Service, not a Deployment)
- Defines a class with identical pods
- EPP picks from the instances defined here

**Analogy:** Like a class definition with N objects. EPP picks which object serves the request.

---

### Admission & Placement

**Admission:** Should we accept this request at all?
- Checks: Token quota, queue depth, SLA/SLO
- Decision: Accept (200) or shed (429/503)

**Placement:** If accepted, where does it go?
- Checks: Which pod has capacity?
- Decision: Route to pod or overflow to Superlinked

**Shedding:** Deliberately refusing work
- Reason: Exceeds SLA/SLO or capacity limits
- Response: 429 (tenant quota) or 503 (no pod)

---

## Key Learnings from This Class

1. **Admission control works** — System sheds load when overloaded (by design)
2. **Different tools, different jobs:**
   - HAMi = resource allocation
   - KEDA = reactive scaling
   - Mooncake = KV transfer
   - Locust = system benchmark

3. **KV hops require split=phase** — Prefill and decode on separate pods
4. **Mooncake enables cross-pod sharing** — KV cache can be used by multiple pods
5. **Locust measures orchestration, not model** — It's testing your admission policy

---

## Study Checklist

- [ ] Understand what HAMi does (and doesn't do)
- [ ] Know KEDA operates at tens-of-seconds scale (not per-request)
- [ ] Explain KV cache to someone (what it is, why it matters)
- [ ] Describe Mooncake's role (when and why needed)
- [ ] Distinguish SSE from WebSocket
- [ ] Explain Locust measures orchestration, not model speed
- [ ] Calculate prefill:decode ratio for your model
- [ ] Estimate safe concurrency for 40GB machine

---

**Next:** Deploy with `split=phase` to enable KV hops and see Mooncake transfer engine in action! 🚀
