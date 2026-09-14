# Class 9b — Workload vs Tooling Matrix

**The complete decision matrix: pick your workload, and every tool column answers for you.**

---

## The Matrix at a Glance

| Workload Target | Gateway & Routing | KV Transfer & Cache | Device Plane | Scaling Driver |
|-----------------|-------------------|---------------------|--------------|-----------------|
| **Agentic / RAG** | GIE EPP / llm-d | Mooncake / LMCache | K8s DRA (Dedicated) | KEDA (Active Tokens) |
| **Low-Latency Chat** | NVIDIA Dynamo Router | In-Engine APC Only | NVIDIA MIG / MPS | Dynamo Planner |
| **Offline Batch** | Ray Serve LLM / vLLM | In-Engine APC Only | HAMi (vGPU Slicing) | KEDA (Queue Depth) |
| **Multimodal Pipeline** | OurRouter + kgateway | LMCache / APC | K8s DRA + Volcano | HPA on Concurrency |

---

## Reading the Matrix

**Example: You're building an agentic system (multi-turn conversations with RAG)**

| Plane | Tool | Why |
|-------|------|-----|
| **Gateway & Routing** | GIE EPP / llm-d | Prefix-aware routing (same conversation sticks together) |
| **KV Transfer** | Mooncake / LMCache | Long conversations need KV reuse across pod boundaries |
| **Device** | K8s DRA (Dedicated) | Agents need reliable resource allocation, not time-slicing |
| **Scaling** | KEDA (Active Tokens) | Scale by tokens in flight (not just concurrency) |

**Your stack:** GIE EPP + Mooncake + K8s DRA + KEDA  
**This stack is optimized for:** Long-running conversations with shared prefix and KV reuse

---

## Real-World Examples

### 🤖 **Agentic / RAG Systems**
**Use case:** Multi-turn agents, document Q&A, retrieval-augmented generation

```
Gateway: GIE EPP / llm-d
  → Prefix-aware routing
  → Sticky until pod saturates
  → Conversation history is precious

KV: Mooncake / LMCache
  → Transfer KV between pods
  → Multiple documents cached
  → Long context reuse

Device: K8s DRA (Dedicated)
  → Guaranteed resources
  → No preemption
  → Conversation state safe

Scaling: KEDA (Active Tokens)
  → Scale by tokens in flight
  → Predictive (look ahead)
  → Never scale to zero
```

**Real companies:** OpenAI Assistants, Claude Projects, LangChain agents

---

### ⚡ **Low-Latency Chat**
**Use case:** Real-time chat, code completion, quick responses

```
Gateway: NVIDIA Dynamo Router
  → Aggregated routing
  → Route on active requests + KV
  → Fast decision-making

KV: In-Engine APC Only
  → No KV transfer (not worth it)
  → Prefix cache within pod
  → Each conversation isolated

Device: NVIDIA MIG / MPS
  → Fixed slices or time-sharing
  → Low latency over throughput
  → Rapid pod turnover

Scaling: Dynamo Planner
  → Predictive scaling
  → Look ahead 30s
  → Prepare pods before load
```

**Real companies:** ChatGPT, Claude Chat, GitHub Copilot

---

### 📊 **Offline Batch**
**Use case:** Model evaluation, embeddings generation, data augmentation

```
Gateway: Ray Serve LLM / vLLM
  → Actor pool (stateless)
  → No KV awareness needed
  → Throughput focused

KV: In-Engine APC Only
  → No transfer (batch is stateless)
  → Prefix cache irrelevant
  → Each request independent

Device: HAMi (vGPU Slicing)
  → Aggressive slicing
  → Maximize utilization
  → Cost per inference matters

Scaling: KEDA (Queue Depth)
  → Scale by jobs waiting
  → Queue backlog is metric
  → Batch work is best-effort
```

**Real companies:** Model benchmarking, synthetic data generation, embedding services

---

### 🎨 **Multimodal Pipeline**
**Use case:** Image + text processing, visual Q&A, multi-modal analysis

```
Gateway: OurRouter + kgateway
  → Split text and vision pools
  → Text pool never sees images
  → Separate scaling per modality

KV: LMCache / APC
  → Vision might not use KV
  → Text uses LMCache
  → Different cache strategies

Device: K8s DRA + Volcano
  → Different resource requirements
  → Vision needs GPU memory
  → Text needs compute
  → Cluster-wide scheduling

Scaling: HPA on Concurrency
  → Different ratios per modality
  → Text and vision scale independently
  → Per-pool concurrency limits
```

**Real companies:** Open WebUI, multi-modal RAG systems, image understanding APIs

---

## Your Lab: Mixed Workload

| Aspect | Current Choice | Why |
|--------|---|---|
| **Workload** | Mixed chat + overflow | 70% text, 20% vision, 10% audio |
| **Gateway & Routing** | Gateway API EPP | Admission + placement decisions |
| **KV Transfer & Cache** | Mooncake (split=phase) | Prefill→decode KV transfers |
| **Device Plane** | HAMi (16GB slices) | Flexible GPU allocation |
| **Scaling Driver** | KEDA (tokens in flight) | Reactive scaling on load |

**Why this combination works:**
- Text requests (70%) → local, sticky routing with KV reuse
- Vision/audio (30%) → overflow to Superlinked
- Prefill/decode split → enables KV hops
- KEDA scales based on tokens, not just concurrency

---

## How to Read This for Your Own Workload

1. **Identify your workload type:**
   - Multi-turn conversations? → Agentic / RAG
   - Real-time responses? → Low-Latency Chat
   - Bulk processing? → Offline Batch
   - Multiple modalities? → Multimodal Pipeline
   - Mix? → Blend appropriate columns

2. **Read down each column:**
   - Gateway & Routing tool
   - KV Transfer & Cache tool
   - Device Plane tool
   - Scaling Driver tool

3. **Implement that stack:**
   - Each tool solves one plane's question
   - They work together to optimize for your workload
   - Swapping one tool = changing one plane (safe)

---

## Decision Tree

**Start here to find your workload:**

```
Does your workload have multi-turn conversations?
  YES → Agentic / RAG
         (prefix matters, KV reuse critical)
  NO → Go to next question

Do you need sub-100ms response times?
  YES → Low-Latency Chat
         (minimize hops, in-engine cache only)
  NO → Go to next question

Do you process batches without latency targets?
  YES → Offline Batch
         (maximize throughput, aggressive slicing)
  NO → Go to next question

Do you handle multiple modalities (text + vision)?
  YES → Multimodal Pipeline
         (separate pools, different strategies)
  NO → Hybrid (you're mixing patterns)
```

---

## Study Questions

- [ ] Why would you pick Mooncake over in-engine cache?
- [ ] Why does Agentic/RAG use KEDA (Active Tokens) but Batch uses KEDA (Queue Depth)?
- [ ] If you switch from Low-Latency Chat to Agentic, which THREE columns must you change?
- [ ] For Multimodal Pipeline, why can't vision requests use the text pod?
- [ ] Which workload can NOT use prefix-aware routing?

---

## Practical: Your Next Decision

**Scenario:** "We're adding long-context document analysis to our chat system."

**Analysis:**
- Current: Low-Latency Chat
- New requirement: Agentic (long context + document memory)
- What needs to change?

**Answer (read from matrix):**
- Gateway: NVIDIA Dynamo Router → GIE EPP (need prefix-aware, not just aggregated)
- KV: In-Engine APC → Mooncake (need KV transfers for document context)
- Device: NVIDIA MIG → K8s DRA (need guaranteed resources for conversations)
- Scaling: Dynamo Planner → KEDA Active Tokens (predictive → reactive is safer)

**Result:** You're now running the Agentic / RAG stack. All other parts stay the same.

---

## The Power of This Matrix

> **Every cell answers one plane's question for one workload type. Once you know your workload, every tool choice is determined.**

This means:
- ✅ Architecture discussions become concrete ("are we Agentic or Batch?")
- ✅ Tool evaluations stay focused ("how does this fit the Chat column?")
- ✅ Tradeoffs are clear ("Chat uses MIG for speed; RAG uses DRA for reliability")
- ✅ Scaling discussions are grounded ("what's our workload target?")

---

**Next: Test your current stack (Mixed chat with split=phase) and see it work!** 🚀

Your lab is running:
- ✅ Mixed chat workload
- ✅ Gateway EPP routing
- ✅ Mooncake KV transfers (split=phase)
- ✅ HAMi device slicing
- ✅ KEDA active tokens scaling

Test KV hops and verify! 🎯
