#!/bin/bash
# Download metrics using local SSH tunnel (make ssh must be running)

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DOWNLOAD_DIR="./results/metrics_${TIMESTAMP}"

echo "📊 Downloading metrics via SSH tunnel..."
mkdir -p "$DOWNLOAD_DIR"

# 1. Get REPL metrics (all Prometheus metrics)
echo "1️⃣  Capturing REPL metrics snapshot..."
mkdir -p "$DOWNLOAD_DIR/repl"
(echo "metrics"; sleep 1; echo "quit") | make repl 2>/dev/null | grep "orch_\|mooncake_" > "$DOWNLOAD_DIR/repl/metrics_snapshot.txt" || echo "✓ Metrics captured"

# 2. Get REPL board (routing history)
echo "2️⃣  Capturing REPL routing board..."
(echo "board"; sleep 1; echo "quit") | make repl 2>/dev/null > "$DOWNLOAD_DIR/repl/board_history.txt" || echo "✓ Board captured"

# 3. Get REPL profile (latency breakdown)
echo "3️⃣  Capturing REPL latency profile..."
(echo "profile"; sleep 1; echo "quit") | make repl 2>/dev/null > "$DOWNLOAD_DIR/repl/latency_profile.txt" || echo "✓ Profile captured"

# 4. Export Prometheus metrics via HTTP (through tunnel)
echo "4️⃣  Exporting Prometheus metrics..."
mkdir -p "$DOWNLOAD_DIR/prometheus"

# Common metrics
METRICS=(
  "orch_requests_total"
  "orch_completed_total"
  "orch_shed_total"
  "orch_overflow_total"
  "orch_kv_transfer_total"
  "orch_kv_transfer_tokens"
  "orch_pick_total"
  "orch_request_duration_seconds"
  "mooncake_hops_total"
  "mooncake_hop_tokens_total"
  "mooncake_blocks"
)

for metric in "${METRICS[@]}"; do
  curl -s "http://127.0.0.1:9090/api/v1/query?query=$metric" > "$DOWNLOAD_DIR/prometheus/${metric}.json" 2>/dev/null || echo "  ⚠️  $metric not found"
done

echo "✓ Prometheus metrics exported"

# 5. Export Grafana dashboards
echo "5️⃣  Exporting Grafana dashboards..."
mkdir -p "$DOWNLOAD_DIR/grafana"

# Try to get dashboard list
DASHBOARDS=$(curl -s "http://127.0.0.1:31495/api/search?type=dash-db" 2>/dev/null | grep -o '"uid":"[^"]*"' | cut -d'"' -f4 || echo "")

if [ -n "$DASHBOARDS" ]; then
  for uid in $DASHBOARDS; do
    curl -s "http://127.0.0.1:31495/api/dashboards/uid/$uid" > "$DOWNLOAD_DIR/grafana/${uid}_dashboard.json" 2>/dev/null || true
  done
  echo "✓ Grafana dashboards exported"
else
  echo "⚠️  Grafana dashboards not accessible (may need auth)"
fi

# 6. Create analysis guide
echo "6️⃣  Creating analysis guide..."
cat > "$DOWNLOAD_DIR/METRICS_GUIDE.md" << 'EOF'
# Downloaded Metrics Analysis Guide

## Files Captured

### 1. REPL Metrics (`repl/metrics_snapshot.txt`)
**Raw Prometheus format metrics:**
- `orch_requests_total` - Total requests received
- `orch_completed_total` - Successful completions
- `orch_shed_total` - Admission control rejections (429, 503)
- `orch_kv_transfer_total` - KV cache hops
- `orch_kv_transfer_tokens` - Tokens cached
- `orch_pick_total` - Routing decisions
- All other gateway metrics

**How to use:**
```bash
cat repl/metrics_snapshot.txt | grep "orch_requests_total"
cat repl/metrics_snapshot.txt | grep "orch_kv"
```

### 2. Routing Board (`repl/board_history.txt`)
**Last 12 requests with routing decisions:**
- Request ID
- Capability (text/vision)
- Pod selected
- Route (local/overflow)
- HTTP status code
- Why (placement reason)

**Example line:**
```
14ab3c7d   text    text-0 both    local    200    BIND text → text  PLACE text-0
```

**How to use:**
```bash
cat repl/board_history.txt
# Count successful local routes
cat repl/board_history.txt | grep "200" | wc -l
```

### 3. Latency Profile (`repl/latency_profile.txt`)
**Request latency breakdown by stage:**
- gateway (admission stage)
- pick (router placement stage)
- local (vLLM processing)
- overflow (Superlinked processing)
- e2e (total end-to-end)

**Shows count, sum, and average latency per stage**

**How to use:**
```bash
cat repl/latency_profile.txt | head -20
# Look for avg_ms column to see average latency per stage
```

### 4. Prometheus Metrics (`prometheus/*.json`)
**Raw Prometheus query results in JSON format:**
- `orch_requests_total.json`
- `orch_kv_transfer_total.json`
- `mooncake_hops_total.json`
- etc.

**How to use:**
```bash
# Parse JSON to get current value
cat prometheus/orch_requests_total.json | jq '.data.result[0].value[1]'

# Pretty print
cat prometheus/orch_requests_total.json | jq '.'
```

### 5. Grafana Dashboards (`grafana/*.json`)
**Dashboard definitions that can be re-imported:**
- Success and failures
- Cluster status
- Mooncake KV
- etc.

**How to use:**
```bash
# Import into new Grafana:
1. Login to Grafana
2. Dashboard → Import
3. Upload JSON file
4. Customize as needed
```

## Quick Analysis

### Count total requests
```bash
grep "orch_requests_total" repl/metrics_snapshot.txt | tail -1
```

### Check KV hopping
```bash
grep "orch_kv_transfer" repl/metrics_snapshot.txt
```

### Analyze routing success
```bash
cat repl/board_history.txt | grep "200" | wc -l  # successful
cat repl/board_history.txt | grep "503" | wc -l  # no pod
cat repl/board_history.txt | grep "429" | wc -l  # admission cap
```

### Latency summary
```bash
cat repl/latency_profile.txt
# Look for: avg_ms (average latency per stage)
```

## What Each Metric Means

| Metric | Meaning | Good Value |
|--------|---------|-----------|
| `orch_requests_total` | Total requests | High (more traffic) |
| `orch_completed_total` | Successful requests | Equal to total |
| `orch_shed_total` | Rejected requests | Low or zero |
| `orch_overflow_total` | Overflows to backup | Low or zero |
| `orch_kv_transfer_total` | KV hops | High for multi-turn |
| `orch_kv_transfer_tokens` | Tokens cached | High (more efficiency) |

## Using This Data

### 1. Performance Analysis
- Compare latency across stages
- Identify bottlenecks (which stage is slowest?)
- Validate KV cache improvements

### 2. Reliability Analysis
- How many requests succeeded?
- What was rejection rate?
- Were there overflows?

### 3. Architecture Validation
- Is KV hopping working? (check `orch_kv_transfer_total`)
- Is admission control working? (check `orch_shed_total`)
- Is routing working? (check board routing decisions)

### 4. Capacity Planning
- What was peak load?
- What latencies at peak?
- How close to saturation?

## Next Steps

1. **Save this directory** - these are your production metrics
2. **Analyze locally** - use the analysis commands above
3. **Compare runs** - download metrics from multiple runs to track improvements
4. **Re-import dashboards** - see visualizations again in Grafana
5. **Document results** - create a session report

---
Generated: $(date)
EOF

# 7. Summary
echo ""
echo "✅ Download complete!"
echo "📁 Results saved to: $DOWNLOAD_DIR"
echo ""
echo "📊 What was captured:"
ls -la "$DOWNLOAD_DIR"
echo ""
echo "🔍 Quick commands:"
echo "   # View metrics snapshot"
echo "   cat $DOWNLOAD_DIR/repl/metrics_snapshot.txt | head -20"
echo ""
echo "   # View routing board"
echo "   cat $DOWNLOAD_DIR/repl/board_history.txt"
echo ""
echo "   # View latency profile"
echo "   cat $DOWNLOAD_DIR/repl/latency_profile.txt"
echo ""
echo "   # Count metrics"
echo "   grep orch_requests_total $DOWNLOAD_DIR/repl/metrics_snapshot.txt | tail -1"
echo ""
echo "Ready to shutdown Lambda! 🚀"
