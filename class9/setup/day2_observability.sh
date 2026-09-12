#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/setup/_lambda_only.sh"
cd "$ROOT"

export KUBECONFIG="${KUBECONFIG:-/etc/rancher/k3s/k3s.yaml}"

echo "== Prometheus (helm) =="
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
helm repo update prometheus-community >/dev/null
helm upgrade --install prometheus prometheus-community/prometheus \
  --namespace monitoring \
  --create-namespace \
  --set server.persistentVolume.enabled=false \
  --set alertmanager.enabled=false \
  --set kube-state-metrics.enabled=false \
  --set prometheus-node-exporter.enabled=false \
  --set prometheus-pushgateway.enabled=false \
  --wait --timeout 10m

echo "== Grafana (helm) =="
helm repo add grafana https://grafana.github.io/helm-charts >/dev/null
helm repo update grafana >/dev/null
helm upgrade --install grafana grafana/grafana \
  --namespace monitoring \
  --set persistence.enabled=false \
  --set service.type=NodePort \
  --wait --timeout 10m

echo
echo "Day 2 is up. Teach, in this order:"
echo "  1. Scrape GET /metrics from orch-serve and vLLM — names you froze on Day 1."
echo "  2. Grafana: orch_kv_free_ratio, orch_kv_transfer_*, orch_kv_evict_total,"
echo "     orch_shed_total, orch_overflow_total, vllm:gpu_cache_usage_perc."
echo "  3. KV eviction: flood until the slice is hot, then evict — BlockRemoved"
echo "     must drop the prefix from kvbus or the Router routes on a ghost cache."
echo "  4. nvidia-smi on the node vs gpumem the HAMi slice reports inside the pod."
echo
echo "Grafana NodePort + admin password:"
kubectl -n monitoring get svc grafana
kubectl -n monitoring get secret grafana -o jsonpath='{.data.admin-password}' | base64 -d
echo
echo "Do not reimplement epp.py. Point the scraper at this build."
