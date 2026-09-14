# Class 9b — Five Planes, Five Questions

**The most common design failure in this course is answering one plane's question in another plane's code.**

---

## The Framework

Each plane asks one question. Each tool answers that question. They must stay in their plane!

### 🔴 **Northbound** — Overflow
**Tool:** Overflow → Superlinked  
**Question:** Should this request leave our cluster at all?  
**Unit of decision:** One call to one backend API  
**Must never decide:** Retrying a local token-cap 429 (that's admission's job)

---

### 🟡 **Gateway + Routing** — Admission + Router (EPP)
**Tool:** admission + router (EPP)  
**Question:** Do we admit it, and which pod and phase serves it?  
**Unit of decision:** One request, one hop (prefill→decode)  
**Must never decide:** In what order work runs on the GPU (that's the GPU's job)

---

### 🟢 **KV Transfer + Cache** — Mooncake (or nothing)
**Tool:** Mooncake, or nothing  
**Question:** Where does cached attention state live, and can another pod have it?  
**Unit of decision:** A block of KV  
**Must never decide:** Which pod is picked (that's routing's job)

---

### 🔵 **Device** — HAMi
**Tool:** HAMi  
**Question:** How much GPU may this pod see?  
**Unit of decision:** MiB of gpumem, % of gpucores  
**Must never decide:** Which request goes where (that's routing's job)

---

### 🟣 **Scaling** — KEDA
**Tool:** KEDA  
**Question:** How many pods exist?  
**Unit of decision:** desired replicas, per Deployment  
**Must never decide:** Per-request routing or overflow (that's gateway's job)

---

## The Design Rule

> **Read it as a grid. A row is a question; everything in that row answers the same question a different way. Swapping a tool inside a row is an architecture choice you can defend. Moving a decision across rows is a bug you will spend a week finding.**

---

## Examples of Common Mistakes

### ❌ Mistake 1: Admission decides pod placement
```python
# WRONG - Admission in gateway plane trying to do routing's job
if tokens_available:
    place_on_pod_1()  # ← This is routing's job!
    return 200
else:
    return 429
```

**Why it's wrong:** Admission asks "do we accept it?", routing asks "where does it go?". Mixing them causes bugs where admission doesn't know about pod health, and routing can't override admission's pod choice.

---

### ❌ Mistake 2: Router decides GPU slicing
```python
# WRONG - Router trying to do HAMi's job
if high_latency:
    reduce_gpu_slice(pod)  # ← This is HAMi's job!
    return request
```

**Why it's wrong:** Router decides "which pod", HAMi decides "how much GPU". If router cuts GPU, it doesn't know if the GPU allocation will support the request, leading to in-flight failures.

---

### ❌ Mistake 3: KEDA decides per-request routing
```python
# WRONG - KEDA trying to do routing's job
if load_high:
    route_request_to_newly_scaled_pod()  # ← Routing's job!
```

**Why it's wrong:** KEDA operates on a timescale of tens of seconds. Routing is per-request. They can't be mixed—KEDA just ensures pods exist, routing decides which pod gets a request.

---

## Correct Example: Handling a 503

**Scenario:** Request arrives, no pod has capacity.

**Correct flow:**
1. **Gateway (routing plane):** "I can't find a pod with capacity. Shed or overflow?"
2. **Northbound (overflow plane):** "Send to Superlinked."
3. **Superlinked:** Handles the request externally
4. **KEDA (scaling plane):** Sees metrics, scales up replicas
5. **Next request:** Gateway finds the new pod

**Each layer answers its own question.**

---

## The Five Questions at a Glance

| Plane | Tool | Question | Scope | Answer Format |
|-------|------|----------|-------|----------------|
| **Northbound** | Overflow | Leave cluster? | One API call | YES / NO |
| **Gateway** | EPP | Admit + place? | One request | Pod + phase or SHED |
| **KV** | Mooncake | Share cache? | One KV block | Which pods can access? |
| **Device** | HAMi | GPU amount? | One pod | MiB + % |
| **Scaling** | KEDA | Pod count? | One deployment | Desired replicas |

---

## Why This Matters

**Architectural clarity** = **debugging speed**

When something breaks:
- **429 error?** Check the **gateway plane** (admission logic)
- **503 error?** Check the **gateway plane** (no eligible pod)
- **Latency spike?** Check the **device plane** (HAMi slices) or **KV plane** (cache misses)
- **Pod count wrong?** Check the **scaling plane** (KEDA metrics)
- **Wrong pod picked?** Check the **routing plane** (EPP logic)

**If you look in the wrong plane, you'll never find the bug.**

---

## Study Questions

- [ ] What question does each plane answer?
- [ ] Why can't routing decide pod allocation (that's HAMi's job)?
- [ ] Why can't admission decide overflow (that's northbound's job)?
- [ ] If you see a bug where requests are routed to pods without capacity, which plane is broken?
- [ ] If you see a bug where pods scale but don't get traffic, which two planes might be misaligned?

---

## Key Insight

> Each tool is a specialist. It answers one question really well. The bug happens when you ask it to answer another plane's question in its code.

**This is the difference between elegant systems and ones that take weeks to debug.** 🎯

---

**Next:** When you deploy `split=phase`, watch how each plane handles the new prefill/decode split cleanly! ✨
