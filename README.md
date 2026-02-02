# ZeroTrust-FLBench

**Design-space evaluation of Network Isolation + mTLS/Service Mesh for Federated Learning on Edge Kubernetes**

## Overview

This project evaluates the impact of Zero-Trust security mechanisms (NetworkPolicy + mTLS/service mesh) on Federated Learning (FL) performance in edge/cloud Kubernetes environments. It measures:

- **Round tail-latency** (p50/p95/p99)
- **Time-to-target-accuracy (TTA)**
- **Communication overhead** (bytes/round)
- **Failure/retry rates**
- **Resource overhead** (CPU/memory)

## Research Questions

1. **RQ1:** How do NetworkPolicy (default-deny) and mTLS/service mesh affect FL round latency distribution and failure rates under edge network conditions?
2. **RQ2:** What is the impact on time-to-target-accuracy and communication overhead?
3. **RQ3:** Do "sweet spots" exist that balance security and performance?
4. **(Stretch) RQ4:** Can we create policy-based rules to optimize the security-performance-learning trade-off?

## Three Core Contributions

1. **Design-space map:** Comprehensive evaluation of {NetworkPolicy, mTLS, isolation} × {network conditions} → {latency, accuracy, overhead, failures}
2. **FL-specific methodology:** Proper measurement of round tail-latency, time-to-accuracy, with reproducible statistics
3. **Open benchmark harness:** Scripts + manifests + configs for full reproducibility

## Project Structure

```
ZeroTrust-FLBench/
├── docs/                      # Documentation
│   ├── threat_model.md        # Scope and threat model
│   ├── measurement_method.md  # How we measure FL metrics
│   ├── experiment_matrix.md   # Full experiment design
│   └── security_configs.md    # Security configuration details
├── src/                       # FL application code
│   ├── fl_server.py          # Flower FL server
│   ├── fl_client.py          # Flower FL client
│   ├── models/               # Model definitions
│   └── utils/                # Helper functions
├── k8s/                       # Kubernetes manifests
│   ├── 00-baseline/          # Baseline (no security)
│   ├── 10-networkpolicy/     # NetworkPolicy configs
│   ├── 20-mtls-linkerd/      # Linkerd mTLS
│   └── 30-observability/     # Prometheus/Grafana
├── scripts/                   # Automation scripts
│   ├── run_matrix.py         # Experiment runner
│   ├── netem_apply.sh        # Network emulation
│   ├── netem_reset.sh        # Reset network
│   └── collect_results.py    # Data collection
├── observability/            # Monitoring configs
│   ├── prometheus/
│   └── grafana/
├── results/                  # Experiment results
│   ├── raw/                 # Raw logs and metrics
│   ├── processed/           # Processed data
│   └── figures/             # Generated plots
└── requirements.txt         # Python dependencies
```

## Quick Start

### Prerequisites

- **Kubernetes:** minikube or kind (recommend minikube for better CNI support)
- **Docker**
- **kubectl**
- **Python 3.9+**
- **Linux/Ubuntu** (or WSL2)

### Phase 0: Setup (Day 1)

```bash
# Clone and setup
cd ZeroTrust-FLBench
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start minikube with CNI that supports NetworkPolicy
minikube start --cni=calico --cpus=4 --memory=8192
```

### Phase 1: Baseline FL (Days 2-5)

```bash
# Deploy baseline FL
kubectl apply -f k8s/00-baseline/

# Monitor logs
kubectl logs -f deployment/fl-server
```

### Phase 2: Add Observability (Days 6-10)

```bash
# Deploy Prometheus
kubectl apply -f k8s/30-observability/
```

### Phase 3: Network Emulation (Days 11-13)

```bash
# Apply network profile
./scripts/netem_apply.sh NET2
```

### Phase 4: Security Knobs (Days 14-24)

```bash
# Deploy with NetworkPolicy
kubectl apply -f k8s/10-networkpolicy/

# Deploy with Linkerd mTLS
linkerd install | kubectl apply -f -
kubectl apply -f k8s/20-mtls-linkerd/
```

### Phase 5: Run Experiments (Days 25-38)

```bash
# Run experiment matrix
python scripts/run_matrix.py --config configs/core_matrix.yaml
```

### Phase 6: Generate Results (Days 39-45)

```bash
# Process data and generate figures
python scripts/collect_results.py
jupyter notebook results/analysis.ipynb
```

## Milestones

- ✅ **Milestone 1:** FL baseline running + logging round time + accuracy
- ✅ **Milestone 2:** NetworkPolicy SEC0 vs SEC1 showing measurable differences
- ✅ **Milestone 3:** mTLS SEC2/SEC3 with p95/p99 metrics

## Security Configurations

- **SEC0:** No policy, no mTLS (baseline)
- **SEC1:** NetworkPolicy only (default-deny + allow-list)
- **SEC2:** mTLS only (service mesh)
- **SEC3:** NetworkPolicy + mTLS (full zero-trust)

## Network Profiles

- **NET0:** No impairment (LAN baseline)
- **NET1:** 20ms delay, 5ms jitter
- **NET2:** 80ms delay, 20ms jitter
- **NET3:** 0.5% loss
- **NET4:** 1% loss + jitter
- **NET5:** 5-10 Mbps bandwidth cap

## Citation

If you use this benchmark, please cite:

```bibtex
@article{zerotrust-flbench2026,
  title={ZeroTrust-FLBench: Design-space Evaluation of Network Isolation and mTLS for Federated Learning on Edge Kubernetes},
  author={Your Name},
  journal={Digital Communications and Networks},
  year={2026}
}
```

## License

MIT License

## Contact

[Your contact information]
