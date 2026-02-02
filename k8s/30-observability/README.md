# Prometheus Configuration for ZeroTrust-FLBench

## Overview

This directory contains Prometheus configuration for monitoring FL workloads.

## Quick Setup

### Option 1: Helm (Recommended)

```bash
# Add Prometheus helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values prometheus-values.yaml
```

### Option 2: Manual YAML

```bash
kubectl apply -f prometheus-deployment.yaml
```

## Accessing Prometheus

```bash
# Port forward
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# Open browser
open http://localhost:9090
```

## Key Metrics to Collect

### Container Metrics

```promql
# CPU usage (millicores)
rate(container_cpu_usage_seconds_total{namespace="fl-experiment"}[5m]) * 1000

# Memory usage (MB)
container_memory_working_set_bytes{namespace="fl-experiment"} / 1024 / 1024

# Network TX bytes
rate(container_network_transmit_bytes_total{namespace="fl-experiment"}[1m])

# Network RX bytes
rate(container_network_receive_bytes_total{namespace="fl-experiment"}[1m])
```

### Pod Metrics

```promql
# Pod restarts
kube_pod_container_status_restarts_total{namespace="fl-experiment"}

# Pod phase
kube_pod_status_phase{namespace="fl-experiment"}
```

## Querying for Round Boundaries

The challenge is aligning Prometheus scrapes with FL round boundaries.

**Approach:**

1. FL application logs round start/end timestamps
2. Query Prometheus using exact time ranges
3. Compute delta metrics between round boundaries

**Example Python query:**

```python
import requests
from datetime import datetime

def query_prometheus(metric, start_ts, end_ts, step='15s'):
    """Query Prometheus range"""
    url = 'http://localhost:9090/api/v1/query_range'
    params = {
        'query': metric,
        'start': start_ts,
        'end': end_ts,
        'step': step
    }
    resp = requests.get(url, params=params)
    return resp.json()

# Example: Get network bytes for round 5
round_start = 1675334400  # Unix timestamp from FL log
round_end = 1675334460    # 60 seconds later

result = query_prometheus(
    'container_network_transmit_bytes_total{pod="fl-client-0"}',
    round_start,
    round_end
)

# Compute delta
bytes_sent = result['data']['result'][0]['values'][-1][1] - \
             result['data']['result'][0]['values'][0][1]
```

## Grafana Dashboards

If using kube-prometheus-stack, Grafana is included:

```bash
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
```

**Login:** admin / prom-operator (default)

**Import dashboard:** Use provided `fl-dashboard.json`

## Troubleshooting

### Metrics not appearing

Check ServiceMonitor:

```bash
kubectl get servicemonitor -n monitoring
```

Ensure FL pods have metrics port exposed and labeled correctly.

### High cardinality

If Prometheus is slow, reduce label dimensions:

```yaml
metric_relabel_configs:
  - source_labels: [__name__]
    regex: 'container_(network|cpu|memory).*'
    action: keep
```

---

**Note:** For research purposes, we primarily query Prometheus at end of experiments, not real-time dashboards.

**Last updated:** 2026-02-02
