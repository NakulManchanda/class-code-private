# Class 9b — The Repository is the Same Map

**Every directory owns exactly one plane's question. If a file needs to know about two, it is in the wrong place.**

---

## The Directory Structure = The Five Planes

```
k8s-config/          ← The cluster
├── hami/            ← Device plane: GPU slicing
├── router/keda*     ← Scaling plane: Autoscaling
├── ui/open-webui.yaml
└── observability/   ← Observability (cross-cutting)

app/                 ← Application layer: Edge policy
├── guardrails.py    ← What requests are allowed (load gen)
├── locustfile.py    ← Load testing (load gen)
└── crew_flood.py    ← Flood testing (load gen)

gateway/             ← Gateway plane: Admission
├── serve.py         ← HTTP surface, tenant budgets, REPL
└── admission.py     ← "Do we admit?"

router/              ← Router plane: Placement & KV
├── planner.py       ← "Which pod + phase?" (placement)
├── kv_bus.py        ← KV cache transfer (Mooncake client)
└── overflow.py      ← "Should we send to Superlinked?"

repl.py              ← Testing harness
```

---

## What Each Directory Owns

### 🟡 **app/** — Application Layer

**Owns:** Edge policy, load generation, the agent flood script  
**Question it answers:** "What should the request look like as text?"

**Contains:**
- `guardrails.py` — Edge policy (what's allowed)
- `locustfile.py` — Load test prompts (text forms)
- `crew_flood.py` — Flood test script

**Must NOT import:**
- ❌ Router internals (placement logic)
- ❌ Scorer logic

---

### 🟡 **gateway/** — Gateway Plane (Admission)

**Owns:** HTTP surface, tenant budgets, REPL  
**Question it answers:** "Do we admit this request?"

**Contains:**
- `serve.py` — HTTP endpoint, budget tracking
- `admission.py` — Admission logic (token cap, queue depth)
- `repl.py` — Interactive testing

**Must NOT import:**
- ❌ Pool mutations (that's router's job)
- ❌ Placement decisions

---

### 🟡 **router/** — Router Plane (Placement + KV)

**Owns:** Placement, worker client, KV bus, overflow  
**Question it answers:** "Which pod + phase should serve this?"

**Contains:**
- `planner.py` — Placement decisions (pick pod)
- `kv_bus.py` — KV cache transfers (Mooncake client)
- `overflow.py` — Send to Superlinked when needed

**Must NOT import:**
- ❌ HTTP concerns (gateway's job)
- ❌ KEDA replica count (scaling's job)

---

### 🟡 **k8s-config/** — Device + Scaling Planes

**Owns:** HAMi slices, KEDA scalers, UI, observability  
**Question it answers:** "How many pods? How much GPU?"

**Contains:**
- `hami/` — GPU slice allocation (Device plane)
- `router/keda*.yaml` — Autoscaling rules (Scaling plane)
- `ui/open-webui.yaml` — UI deployment
- `observability/` — Prometheus, Grafana, DCGM

**Must NOT import:**
- ❌ Business logic (gateway's job)
- ❌ Placement algorithms (router's job)

---

## The Rules

### ✅ Correct: Staying in Your Plane

```python
# gateway/serve.py (Admission plane)
if tenant_tokens_remaining < request_tokens:
    return 429  # ✅ Correct: admission decides to shed
else:
    call_router()  # ✅ Correct: pass to router for placement
```

### ❌ Wrong: Crossing Planes

```python
# gateway/serve.py (Admission plane)
if pod_has_capacity:  # ❌ WRONG: that's router's job!
    place_on_pod()
    return 200
```

**Why it's wrong:**
- Gateway doesn't know about pod health
- Router might disagree with placement
- You've tangled two planes

---

### ✅ Correct: Router Stays Focused

```python
# router/planner.py (Router plane)
def place(request):
    # ✅ Correct: "which pod has capacity?"
    eligible_pods = get_pods_for_capability(request)
    if eligible_pods:
        return pick_best_pod(eligible_pods)
    else:
        # ✅ Correct: can't place locally, go to overflow
        return overflow_to_superlinked()
```

### ❌ Wrong: Router Tries Admission

```python
# router/planner.py (Router plane)
if tenant_tokens_remaining < request_tokens:  # ❌ WRONG!
    return 429  # ❌ That's admission's job!
```

**Why it's wrong:**
- Admission already checked this
- Router shouldn't re-check admission decisions
- You've tangled two planes

---

## Reading the Code by Plane

**When something breaks, know which directory to look in:**

| Symptom | Plane | Directory |
|---------|-------|-----------|
| Request rejected (429) | Gateway | `gateway/admission.py` |
| Request has no pod (503) | Router | `router/planner.py` |
| Pod count wrong | Scaling | `k8s-config/router/keda*.yaml` |
| GPU allocation wrong | Device | `k8s-config/hami/` |
| KV not transferred | KV Transfer | `router/kv_bus.py` |
| Wrong requests to wrong model | App/Gateway boundary | `app/guardrails.py` + `gateway/serve.py` |

---

## Your Current Codebase (split=phase)

**What changed when you set `LAB_SPLIT = "phase"`?**

- ✅ `k8s-config/gateway/orch-serve.yaml` — Added environment var
- ✅ `router/planner.py` — Now routes to prefill OR decode (not both)
- ✅ `router/kv_bus.py` — Now needed (transfers KV between pods)
- ✅ No changes to `gateway/admission.py` — Still answers "do we admit?"
- ✅ No changes to `app/` — Still generates same requests

**Each directory stayed focused on its plane.** ✨

---

## The Design Principle

> **Every Python file owns exactly one plane. If it needs to know about two planes, it's in the wrong file.**

**This makes:**
- ✅ Debugging fast (one plane = one directory)
- ✅ Refactoring safe (change one plane without breaking others)
- ✅ Testing clean (test one plane at a time)
- ✅ Onboarding easy (new teammate learns one plane per directory)

---

## Study Questions

- [ ] Where would you add logic to decide "do we admit this request"? (gateway/)
- [ ] Where would you add logic to pick which pod serves it? (router/)
- [ ] If you need to change GPU allocation, where do you edit? (k8s-config/hami/)
- [ ] If planner.py imports admission.py, what's the problem? (tangled planes)
- [ ] Where does the load generator live? (app/) Why not in router/? (app owns edge policy, not routing)

---

## Refactoring Safely

**Scenario:** "We want to try a different placement algorithm"

**Safe approach:**
1. Edit only `router/planner.py` (Router plane)
2. Don't touch gateway (Admission plane)
3. Don't touch k8s-config (Device/Scaling planes)
4. Don't touch app (Application layer)
5. Result: Only one plane changed, others unaffected ✓

**Unsafe approach:**
```python
# DON'T DO THIS
gateway/serve.py:  # Admission plane
    new_placement_logic()  # ❌ Router logic in gateway!
```

---

## Architecture as Code

> The directory structure IS the five planes. You can read the architecture by looking at the folders, and you can read the folders by understanding the planes.

**This is why:**
- `gateway/` is shallow (one plane = one decision)
- `router/` is complex (placement + KV + overflow interactions)
- `k8s-config/` is configuration (declarative, not imperative)
- `app/` is separate (edge policy, not orchestration)

---

**Next: Test KV hops and see these planes work together!** 🚀

The code organization mirrors the architecture — once you understand that, reading and modifying the code becomes straightforward.
