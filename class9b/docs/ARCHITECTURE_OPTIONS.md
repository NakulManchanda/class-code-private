# Class 9b — Architecture Options: Five Planes, Multiple Implementations

**Everything in a row answers that row's question a different way.**

---

## The Five Planes & Their Options

### 🔴 **Northbound — Overflow Handlers**

**Question:** Should this request leave our cluster?

**Options you can swap:**
- **Superlinked** (ours) — Paid API fallback, good for vision/audio
- **OpenAI / Anthropic direct** — Direct API calls to competitor models
- **Bedrock** — AWS managed model service
- **Vertex** — Google's managed model service
- **OpenRouter** — Model aggregator / router
- **LiteLLM proxy** — Unified API wrapper
- **A sibling cluster** — Route to another internal cluster

**Key insight:** You pick ONE overflow handler. Swapping it is just a config change.

---

### 🟡 **Gateway + Routing — Request Routing**

**Question:** Do we admit it, and which pod serves it?

**Options you can swap:**
- **Gateway API Inference Extension (ours)** — Custom EPP in our gateway
- **llm-d** — Distributed routing
- **NVIDIA Dynamo Router** — NVIDIA's routing layer
- **AIBrix** — Routing as a service
- **Ray Serve LLM** — Ray's LLM routing
- **KServe** — Kubernetes native serving

**Key insight:** Different routers have different capabilities. Some are stateless, some maintain routing history. The interface stays the same: "admit + place or shed".

---

### 🟢 **KV Transfer + Cache — Cache Management**

**Question:** Where does cached attention state live, and can another pod have it?

**Options you can swap:**
- **NIXL (RDMA / NVLink)** — High-speed GPU-to-GPU transfer (HBM to HBM)
- **LMCache** — Distributed KV cache with routing awareness
- **Mooncake** (ours) — KV transfer engine with eviction policies
- **In-engine prefix cache only** — No transfer, just prefix cache within one pod

**Key insight:** More advanced = more complexity. Mooncake handles transfer + policies. LMCache adds routing awareness. NIXL goes direct GPU-GPU. Choose based on your cluster topology.

---

### 🔵 **Device — GPU Slicing**

**Question:** How much GPU may this pod see?

**Options you can swap:**
- **HAMi** (ours) — GPU slicing via CUDA call interception
- **NVIDIA MIG** — Multi-Instance GPU (fixed slices per GPU)
- **Time-slicing** — Pods share GPU, round-robin scheduling
- **MPS** — Multi-Process Service (NVIDIA's older sharing tech)
- **Kubernetes DRA** — Dynamic Resource Allocation (native K8s)
- **Volcano** — Volcano scheduler's GPU management
- **Kueue** — Kueue's resource quotas

**Key insight:** HAMi is most flexible (arbitrary slices). MIG is fixed. Time-slicing is coarse-grained. Each trades flexibility for complexity.

---

### 🟣 **Scaling — Replica Management**

**Question:** How many pods exist?

**Options you can swap:**
- **KEDA** (ours) — Event-driven autoscaler on Prometheus metrics
- **HPA + custom metrics** — Kubernetes HPA with custom metrics
- **Dynamo Planner** — Predictive scaling (looks ahead)
- **Karpenter / Cluster Autoscaler** — Node-level scaling (different layer!)
- **Knative** — Knative's autoscaling

**Key insight:** KEDA is reactive (responds to metrics). Dynamo is predictive (looks ahead). HPA is the K8s default. Karpenter/Cluster Autoscaler scale nodes, not pods.

---

## The Key Principle

> **Hold the top row most loosely of all: every name in it is a base URL and a model id behind the same call. That is the least interesting decision on this slide.**

**Translation:** Your choice of overflow handler (Superlinked vs OpenAI vs Bedrock) is the LEAST important. The architecture that matters is how you route locally, cache KV, slice GPUs, and scale.

---

## What You're Running Today

| Plane | Tool | Implementation |
|-------|------|-----------------|
| **Northbound** | Superlinked | Paid API fallback for overflow |
| **Gateway** | Gateway API EPP | Custom routing in orch-serve |
| **KV Transfer** | Mooncake | KV transfer + eviction policies |
| **Device** | HAMi | Flexible GPU slicing |
| **Scaling** | KEDA | Prometheus-driven autoscaling |

---

## Upgrade Paths

**Want to scale to 100 GPUs?**
- Swap Scaling: KEDA → Dynamo Planner (predictive)
- Swap Device: HAMi → Volcano (cluster-wide scheduling)
- Swap Northbound: Superlinked → Vertex (scale as your own cluster grows)

**Want lower latency KV transfer?**
- Swap KV: Mooncake → NIXL (direct GPU-GPU via RDMA)

**Want more intelligent routing?**
- Swap Gateway: EPP → llm-d (distributed routing with history)

**Each swap is surgical** — you change one plane, the others stay the same.

---

## Study Questions

- [ ] Why is the Northbound choice the least interesting?
- [ ] What's the difference between HAMi and MIG for GPU slicing?
- [ ] Why would you pick Dynamo over KEDA?
- [ ] If you needed KV-aware routing, which two planes interact?
- [ ] What happens if you use NIXL (GPU-GPU) but only have 1 GPU?

---

## Architecture Decisions You Can Defend

✅ "We use HAMi because we need flexible (non-uniform) GPU slices"  
✅ "We use Mooncake because we transfer KV between prefill and decode pods"  
✅ "We use KEDA because we want reactive scaling on request metrics"  
✅ "We use Superlinked because it's simple overflow for non-local models"

❌ "We use Superlinked because it's the best" (arbitrary, not reasoned)  
❌ "We use KEDA because someone told us to" (no justification)  

---

## Next: Test with split=phase!

With `split=phase` enabled:
- **Northbound:** Vision/audio requests → Superlinked (expected)
- **Gateway:** Text requests → orch-serve admission + EPP (expected)
- **KV Transfer:** Prefill pod → Mooncake → Decode pod (should see hops!)
- **Device:** HAMi allocates 16GB to each pod (expected)
- **Scaling:** KEDA scales based on tokens_in_flight (expected)

---

**You now understand the full architecture!** 🎯

Deploy `split=phase` and test KV hops! ✨
