#!/bin/bash
# Download all metrics and results from Lambda before shutdown

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DOWNLOAD_DIR="./results/metrics_${TIMESTAMP}"
LAMBDA_HOST="193.122.152.87"
LAMBDA_USER="ubuntu"

echo "📊 Downloading all metrics and data from Lambda..."
mkdir -p "$DOWNLOAD_DIR"

# 1. Download request traces
echo "1️⃣  Downloading request traces..."
scp -r "${LAMBDA_USER}@${LAMBDA_HOST}:~/class9b/traces/" "$DOWNLOAD_DIR/traces/" 2>/dev/null || echo "⚠️  Traces not found"

# 2. Download logs
echo "2️⃣  Downloading vLLM and gateway logs..."
mkdir -p "$DOWNLOAD_DIR/logs"
scp "${LAMBDA_USER}@${LAMBDA_HOST}:/tmp/vllm-*.log" "$DOWNLOAD_DIR/logs/" 2>/dev/null || echo "⚠️  vLLM logs not found"
scp "${LAMBDA_USER}@${LAMBDA_HOST}:/tmp/mooncake.log" "$DOWNLOAD_DIR/logs/" 2>/dev/null || echo "⚠️  Mooncake log not found"

# 3. Export Prometheus metrics via HTTP
echo "3️⃣  Exporting Prometheus metrics..."
mkdir -p "$DOWNLOAD_DIR/prometheus"
curl -s "http://127.0.0.1:9090/api/v1/query?query=orch_requests_total" > "$DOWNLOAD_DIR/prometheus/requests_total.json" 2>/dev/null || echo "⚠️  Prometheus not accessible"
curl -s "http://127.0.0.1:9090/api/v1/query?query=orch_kv_transfer_total" > "$DOWNLOAD_DIR/prometheus/kv_transfers.json" 2>/dev/null || true
curl -s "http://127.0.0.1:9090/api/v1/query?query=orch_completed_total" > "$DOWNLOAD_DIR/prometheus/completed_total.json" 2>/dev/null || true

# 4. Export Grafana dashboards
echo "4️⃣  Exporting Grafana dashboards..."
mkdir -p "$DOWNLOAD_DIR/grafana"

# Get all dashboard UIDs
DASHBOARDS=$(curl -s "http://127.0.0.1:31495/api/search?type=dash-db" 2>/dev/null | grep -o '"uid":"[^"]*"' | cut -d'"' -f4 || echo "")

if [ -n "$DASHBOARDS" ]; then
  for uid in $DASHBOARDS; do
    echo "  - Exporting dashboard: $uid"
    curl -s "http://127.0.0.1:31495/api/dashboards/uid/$uid" > "$DOWNLOAD_DIR/grafana/${uid}_dashboard.json" 2>/dev/null || true
  done
else
  echo "⚠️  No Grafana dashboards found (may need different auth)"
fi

# 5. Download Kubernetes configurations
echo "5️⃣  Downloading Kubernetes configs..."
mkdir -p "$DOWNLOAD_DIR/k8s-config"
scp -r "${LAMBDA_USER}@${LAMBDA_HOST}:~/class9b/k8s-config/" "$DOWNLOAD_DIR/k8s-config/" 2>/dev/null || echo "⚠️  K8s configs not found"

# 6. Export current pod status
echo "6️⃣  Exporting pod status..."
mkdir -p "$DOWNLOAD_DIR/kubectl"
ssh "${LAMBDA_USER}@${LAMBDA_HOST}" "kubectl get pods -A -o json" > "$DOWNLOAD_DIR/kubectl/pods.json" 2>/dev/null || echo "⚠️  kubectl not accessible via SSH"
ssh "${LAMBDA_USER}@${LAMBDA_HOST}" "kubectl get deploy -A -o json" > "$DOWNLOAD_DIR/kubectl/deployments.json" 2>/dev/null || true
ssh "${LAMBDA_USER}@${LAMBDA_HOST}" "kubectl get svc -A -o json" > "$DOWNLOAD_DIR/kubectl/services.json" 2>/dev/null || true

# 7. Export REPL metrics snapshot
echo "7️⃣  Capturing REPL metrics snapshot..."
mkdir -p "$DOWNLOAD_DIR/repl"
ssh "${LAMBDA_USER}@${LAMBDA_HOST}" "cd ~/class9b && make repl <<< 'metrics' 2>/dev/null" > "$DOWNLOAD_DIR/repl/metrics_snapshot.txt" 2>/dev/null || echo "⚠️  REPL not accessible"

# 8. Download test results
echo "8️⃣  Downloading test results..."
mkdir -p "$DOWNLOAD_DIR/tests"
scp -r "${LAMBDA_USER}@${LAMBDA_HOST}:~/class9b/tests/" "$DOWNLOAD_DIR/tests/" 2>/dev/null || echo "⚠️  Tests not found"

# 9. Create summary document
echo "9️⃣  Creating summary document..."
cat > "$DOWNLOAD_DIR/DOWNLOADED_METRICS.md" << 'EOF'
# Downloaded Metrics and Results

## Contents

### 1. Traces (`traces/`)
- `requests.jsonl` - Complete request logs with timing and routing decisions
- One JSON object per line = one request

### 2. Logs (`logs/`)
- `vllm-text.log` / `vllm-vision.log` - vLLM inference server logs
- `mooncake.log` - KV cache store logs
- Application-level debugging info

### 3. Prometheus Metrics (`prometheus/`)
- `requests_total.json` - Total requests processed
- `kv_transfers.json` - KV cache transfers
- `completed_total.json` - Successful completions
- Raw Prometheus query results

### 4. Grafana Dashboards (`grafana/`)
- Dashboard JSON exports
- Can be re-imported into any Grafana instance
- Includes all visualizations and queries

### 5. Kubernetes Configs (`k8s-config/`)
- Deployment YAML files
- Pod definitions and services
- Configuration for reproducibility

### 6. Pod Status (`kubectl/`)
- `pods.json` - Current pod state snapshot
- `deployments.json` - Deployment status
- `services.json` - Service definitions

### 7. REPL Metrics (`repl/`)
- `metrics_snapshot.txt` - Prometheus metrics dump
- All gateway metrics at time of download

### 8. Test Results (`tests/`)
- Test files and configurations
- Test results if available

## How to Use

### Analyze requests locally
```bash
cat traces/requests.jsonl | jq '.routing, .latency_ms' | head -20
```

### Re-import Grafana dashboards
1. Log into Grafana
2. Dashboard → Import
3. Upload JSON files from `grafana/`

### Query Prometheus data
```bash
# Parse metrics snapshot
cat repl/metrics_snapshot.txt | grep "orch_requests"
```

### Reproduce environment
```bash
cd k8s-config/
kubectl apply -f .
```

## Next Steps

- Analyze request latencies and routing decisions
- Compare with load test results
- Document architecture decisions
- Prepare for next session

---
Generated: $(date)
EOF

# 10. Summary
echo ""
echo "✅ Download complete!"
echo "📁 All files saved to: $DOWNLOAD_DIR"
echo ""
echo "📊 What was captured:"
echo "   - Request traces (requests.jsonl)"
echo "   - Application logs (vLLM, Mooncake, gateway)"
echo "   - Prometheus metrics snapshots"
echo "   - Grafana dashboard definitions"
echo "   - Kubernetes configurations and pod status"
echo "   - REPL metrics at shutdown time"
echo ""
echo "🔍 View contents:"
echo "   ls -la $DOWNLOAD_DIR"
echo ""
echo "📈 Analyze requests:"
echo "   cat $DOWNLOAD_DIR/traces/requests.jsonl | jq '.' | head -20"
echo ""
echo "Ready to shutdown Lambda! 🚀"
