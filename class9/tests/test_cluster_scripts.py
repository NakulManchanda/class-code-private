from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_helm_and_grafana_are_not_on_fakeworker() -> None:
    harness = (ROOT / "fakeworker" / "run.py").read_text()
    assert "helm" not in harness
    assert "kubectl" not in harness
    guard = (ROOT / "setup" / "_lambda_only.sh").read_text()
    assert "Darwin" in guard
    assert "FakeWorker" in guard

def test_day1_cluster_has_keda_not_grafana() -> None:
    day1 = (ROOT / "setup" / "lambda_k3s_hami.sh").read_text()
    assert "kedacore/keda" in day1
    assert "grafana/grafana" not in day1
    assert "helm upgrade --install grafana" not in day1
    day2 = (ROOT / "setup" / "day2_observability.sh").read_text()
    assert "grafana" in day2.lower()
    assert "prometheus" in day2.lower()
    assert "evict" in day2.lower()
