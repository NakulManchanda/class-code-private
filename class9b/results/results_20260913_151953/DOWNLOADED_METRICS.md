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
