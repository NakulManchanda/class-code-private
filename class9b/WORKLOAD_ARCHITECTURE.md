# Class 9b — What You Actually Run: Workload × Architecture

**Your traffic shape picks three of these columns for you. The fourth is usually inherited from your platform team.**

---

## The Decision Matrix

### 📌 **Agents & Multi-turn Chat (Heavy Shared Prefix)**

| Plane | Choice | Why |
|-------|--------|-----|
| **Northbound** | Capacity only — 503 is rare, worth paying for | Agents need reliable execution; overflow too expensive |
| **Gateway** | Prefix-aware routing; sticky until pod saturates | Same conversation reuses prefix; stay on same pod |
| **Device** | MIG or HAMi; generous memory on decode side | Conversation state is precious; don't evict mid-chat |
| **Scaling** | Decode on KV hit; text pool on token backlog | Scale decode by cache hits, text by token demand |

**Example:** OpenAI Assistants, Claude context windows, long-lived agents

---

### 📝 **Long Prompts, Short Answers (RAG, Summarization)**

| Plane | Choice | Why |
|-------|--------|-----|
| **Northbound** | Optional — these are cheap to shed | If prompt fits, answer fast; if not, shed and retry |
| **Gateway** | Split the phases; prefill-heavy fleet | Prefill workload huge, decode workload tiny |
| **Device** | Prefill slices weighted towards compute | Prefill is CPU-bound (attention ops); decode is memory-bound |
| **Scaling** | Uncached prefill tokens in flight | Scale on fresh prefill work, not reuse |

**Example:** Document analysis, meeting summaries, code reviews

---

### 💬 **Short Prompts, Long Answers (Chat, Code Generation)**

| Plane | Choice | Why |
|-------|--------|-----|
| **Northbound** | Real value at peak | Overflow too slow; generate locally |
| **Gateway** | Aggregated usually wins; route on active requests + KV | Pack multiple conversations on one pod |
| **Device** | Decode-shaped slices, more memory | Decode is memory-bound (KV cache grows) |
| **Scaling** | KV utilisation; never scale to zero | KV cache is precious; always keep decode warm |

**Example:** Chatbots, code completion, real-time chat

---

### 📊 **Offline Batch (Evals, Synthetic Data, Embeddings)**

| Plane | Choice | Why |
|-------|--------|-----|
| **Northbound** | None — there is no latency target to protect | Batch work is best-effort |
| **Gateway** | An actor pool; no LLM-aware routing needed | Batch is stateless; no prefix awareness needed |
| **Device** | Aggressive software slicing for utilisation | Fill the GPU; throughput >> latency |
| **Scaling** | Queue backlog depth | Scale by how many jobs are waiting |

**Example:** Model evaluation, embeddings generation, data augmentation

---

### 🎨 **Mixed Text + Multimodal**

| Plane | Choice | Why |
|-------|--------|-----|
| **Northbound** | Capability — image turns leave at bind time | Vision models are scarce; overflow is expected |
| **Gateway** | Split before placement; text pool never sees images | Separate pools for text and vision; different HW |
| **Device** | Size text pool for text share only | Text pool has no vision; don't overallocate |
| **Scaling** | Scale on local share, not total RPS | Text and vision scale independently |

**Example:** Open WebUI, image + text chat, multi-modal RAG

---

## The Honest Reading

> **The skill is not memorising this table. It is knowing which plane's question you are answering, so that when someone proposes a tool you can say which column it belongs in — and therefore what it cannot fix. Row one is the shape our lab is built around.**

---

## How to Use This Table

**Your workload is:** "Multi-turn conversations with document context"  
**Step 1:** Find the row: "Agents & multi-turn chat (heavy shared prefix)"  
**Step 2:** Read across:
- Northbound: Capacity only (no overflow)
- Gateway: Prefix-aware routing
- Device: HAMi with generous decode memory
- Scaling: Decode on KV hit

**Step 3:** If someone suggests "use Superlinked overflow", you say:  
"That's the Northbound plane. Our workload doesn't need it — we need sticky prefix-aware routing (Gateway plane) instead."

---

## Your Current Workload (Class 9b)

You're running a **mixed workload**:

| Type | Percentage | Architecture Impact |
|------|-----------|---------------------|
| Text requests | ~70% | Route to text model (local), sticky routing |
| Vision requests | ~20% | Overflow to Superlinked (no local pod) |
| Audio requests | ~10% | Overflow to Superlinked (no local model) |

**Why `split=phase` helps:**
- Text requests (70%) get local prefill→decode with KV hops
- Vision/audio (30%) overflow, no KV hops needed
- Gateway + routing decides who goes where
- Mooncake transfers KV between prefill and decode

---

## The Architecture Decision Flow

```
1. What's your workload?
   → Multi-turn agents
   → RAG / summarization
   → Chat / code gen
   → Batch
   → Mixed modal

2. For each workload, pick your Northbound
   → Capacity only
   → Optional
   → Real value
   → None
   → Capability-based

3. Pick your Gateway
   → Prefix-aware sticky
   → Split phases
   → Aggregated + KV
   → Actor pool
   → Pre-split by capability

4. Pick your Device
   → Generous decode memory
   → Compute-weighted prefill
   → Memory-weighted decode
   → Aggressive software slicing
   → Separate pools

5. Pick your Scaling
   → KV hit-based
   → Token-based
   → Never-zero decode
   → Queue depth
   → Per-pool independent
```

---

## Study Questions

- [ ] For a chatbot (short prompt, long answer), why is decode-shaped allocation important?
- [ ] For RAG (long prompt, short answer), why do you want a prefill-heavy fleet?
- [ ] For agents (multi-turn), why is prefix-aware routing critical?
- [ ] For batch work, why don't you need prefix-aware routing?
- [ ] If someone says "let's use prefix cache for batch work", which plane are they confusing?

---

## The Real Skill

> Knowing which plane answers which question, so you can evaluate a proposal by asking: "Does this answer the right question for my workload?"

**Useful for:**
- Evaluating new tools ("Is this routing, slicing, or scaling?")
- Debugging ("Which plane is broken?")
- Scaling ("What do I need to change when my workload shifts?")
- Conversations with infrastructure teams ("I need this plane solved differently")

---

**Your lab matches the "Short prompts, long answers" pattern** (decode-heavy chat workload). That's why:
- ✅ `split=phase` gives you separate prefill/decode pods
- ✅ Mooncake transfers KV to the decode pod
- ✅ HAMi gives decode more memory
- ✅ KEDA scales based on tokens in flight

**Test KV hops now!** You're running the right architecture for this workload. 🚀
