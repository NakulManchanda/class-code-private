# Class 9b — REPL Commands & Metrics Reference

**Quick start:**
```bash
make repl
lab> help          # Show all commands
lab> status        # Current cluster
lab> text Hello    # Send request
lab> hop Give me facts  # Test KV hop
```

---

## 📋 All REPL Commands

### Request Commands
| Command | Example | Purpose |
|---------|---------|---------|
| `text` | `lab> text Write a GPU fact` | Send text request to text pod (GPU A) |
| `vision` | `lab> vision Describe this image` | Send vision request to vision pod (GPU B) |
| `audio` | `lab> audio Transcribe this` | Send audio (overflows to Superlinked) |
| `hop` | `lab> hop Give me facts` | **Test KV cache hopping** (prefill→decode) |
| `send` | `lab> send text Hello` | Generic send (same as text/vision/audio) |

### Information Commands
| Command | Purpose |
|---------|---------|
| `status` / `pods` | Show pod inventory, models, and replicas |
| `board` | Show last 12 requests and routing decisions |
| `codes` | Show HTTP status codes and their meanings |
| `metrics` | Dump all Prometheus metrics (gateway format) |
| `profile` | Show latency breakdown by stage (gateway/pick/local/overflow/e2e) |
| `plan` | Show routing plan for next request |
| `healthy` | Check pod health status |

### Configuration Commands
| Command | Example | Purpose |
|---------|---------|---------|
| `replicas` | `lab> replicas 2 2` | Get/set pod count (text/vision or prefill/decode) |
| `slice` | `lab> slice 8192 16384` | Get/set GPU memory per pod (MiB) |
| `split` | `lab> split phase` | Switch topology (capability vs phase) |
| `cap` | `lab> cap 10000` | Get/set token cap per tenant |

### Stress Test Commands
| Command | Example | Purpose |
|---------|---------|---------|
| `flood` | `lab> flood 100` | Send 100 requests rapidly |
| `saturate` | `lab> saturate` | Keep sending until pod saturates |
| `force` | `lab> force 503` | Force a specific HTTP response code |
| `evict` | `lab> evict` | Drop the last hopped KV cache |

### Utility Commands
| Command | Example | Purpose |
|---------|---------|---------|
| `help` / `?` | `lab> help` | Show command help |
| `reset` | `lab> reset` | Reset all metrics/history |
| `quit` / `exit` | `lab> quit` | Exit REPL |

---

## 📊 Key Prometheus Metrics

### Request Flow Metrics
```
orch_requests_total              # Total requests received
orch_completed_total             # Requests completed successfully
orch_shed_total{reason=...}      # Rejected requests (reason: no_eligible_pod, etc)
orch_overflow_total              # Requests sent to backup (Superlinked)
```

### Latency Metrics (Histograms)
```
orch_request_duration_seconds{stage="gateway"}    # Gateway admission latency
orch_request_duration_seconds{stage="pick"}       # Router placement latency
orch_request_duration_seconds{stage="local"}      # Local vLLM latency
orch_request_duration_seconds{stage="overflow"}   # Overflow fallback latency
orch_request_duration_seconds{stage="e2e"}        # End-to-end latency
```

### KV Cache Metrics
```
orch_kv_transfer_total           # Total KV transfers (hops)
orch_kv_transfer_tokens          # Total tokens transferred via KV hops
orch_kv_evict_total              # KV cache evictions
orch_kv_free_ratio               # Fraction of KV capacity free (0.0 to 1.0)
```

### Pod-Level Metrics
```
orch_replica_healthy{pool="...",pod="..."}       # Pod health (1 = healthy)
orch_replica_saturating{pool="...",pod="..."}    # Pod saturation (1 = saturated)
orch_replica_tokens_in_flight{pool="...",pod="..."} # Active tokens on pod
orch_replica_kv_free_ratio{pool="...",pod="..."}   # KV free on pod
orch_replica_running{pool="...",pod="..."}         # Tokens currently running
orch_replica_queue_depth{pool="...",pod="..."}     # Requests waiting in queue
orch_replica_active_requests{pool="...",pod="..."}  # Active requests on pod
```

### Placement & Routing Metrics
```
orch_pick_total                  # Total placement decisions made
orch_sticky_total                # Sticky routing (same pod reused)
orch_place_total{capability="..."} # Placements per capability (text/vision)
orch_planner_desired_replicas{pool="..."} # KEDA desired replica count
```

---

## 🔍 Common Metric Queries

### After sending a text request:
```bash
lab> text Hello world
lab> metrics | grep "orch_requests_total\|orch_completed\|orch_pick_total"
```

Expected output:
```
orch_requests_total 1           # One request received
orch_completed_total 1          # One request completed
orch_pick_total 1               # One placement decision
```

### After testing KV hop:
```bash
lab> hop Give me facts
lab> metrics | grep "orch_kv"
```

Expected output:
```
orch_kv_transfer_total 1                # One KV hop
orch_kv_transfer_tokens 16              # 16 tokens transferred
orch_kv_free_ratio 0.99                 # 99% KV free
```

### Pod health check:
```bash
lab> metrics | grep "orch_replica_healthy"
```

Expected output:
```
orch_replica_healthy{pool="prefill",pod="text-0"} 1      # Healthy
orch_replica_healthy{pool="decode",pod="vision-0"} 1     # Healthy
```

### Saturation test:
```bash
lab> saturate
lab> metrics | grep "orch_replica_saturating"
```

Expected output:
```
orch_replica_saturating{pool="prefill",pod="text-0"} 1   # Saturated
```

---

## 🎯 Workflow Examples

### Example 1: Normal Request Flow
```bash
lab> text Tell me about GPUs
# Output shows: ADMIT ok → PLACE text-0 → ROUTE local → status 200

lab> metrics | grep orch_requests_total
# Shows: orch_requests_total 1

lab> board
# Shows the request in routing history
```

### Example 2: Testing KV Hops
```bash
lab> hop Write a sentence about AI
# Output shows: kv_hop={'src': 'text-0', 'dst': 'vision-0', 'tokens': 16}

lab> metrics | grep orch_kv_transfer
# Shows: orch_kv_transfer_total 1
#        orch_kv_transfer_tokens 16
```

### Example 3: Force a Failure
```bash
lab> force 503
lab> text Test
# Output shows: status=503 (no eligible pod)

lab> metrics | grep orch_shed_total
# Shows: orch_shed_total{reason="no_eligible_pod",code="503"} 1
```

### Example 4: Overflow Test
```bash
lab> audio Transcribe audio
# Audio not supported locally, should overflow

lab> metrics | grep orch_overflow_total
# Shows: orch_overflow_total 1
```

---

## 🔗 How Metrics Flow

```
REPL command (e.g., "text Hello")
    ↓
Gateway receives request
    ↓
Admission checks tokens/quota (orch_requests_total++)
    ↓
Router picks pod (orch_pick_total++, orch_place_total++)
    ↓
vLLM processes locally or Superlinked overflows (orch_overflow_total++)
    ↓
Response returned (orch_completed_total++)
    ↓
Metrics updated (orch_request_duration_seconds{stage=...}, etc)
```

---

## 📈 Grafana Integration

These metrics are scraped by Prometheus (port 9090) and visualized in Grafana:

**Grafana dashboards use these metrics:**
1. **Success and Failures** — `orch_completed_total`, `orch_shed_total`
2. **Cluster** — `orch_replica_tokens_in_flight`, `orch_planner_desired_replicas`
3. **Gateway and Router** — `orch_pick_total`, `orch_place_total`, `orch_shed_total`
4. **Mooncake** — `mooncake_hops_total`, `mooncake_hop_tokens_total`
5. **KEDA** — `orch_planner_desired_replicas`
6. **HAMi** — Pod health and saturation metrics

---

## 🚀 Quick Reference Card

```
Get cluster status:           lab> status
Send text:                    lab> text <prompt>
Test KV hop:                  lab> hop <prompt>
View last 12 requests:        lab> board
See latency breakdown:        lab> profile
Dump metrics (Prometheus):    lab> metrics
Force a 503 error:            lab> force 503
Stress test:                  lab> saturate
```

---

## 📝 Notes

- Metrics are **Prometheus format** (text/plain)
- Pod names: `text-0`, `vision-0` (or `prefill-0`, `decode-0` with split=phase)
- Stages: gateway → pick → local/overflow → e2e
- STAY codes: 200, 429, 500, slice_oom
- LEAVE codes: 503, 529 (trigger overflow)
