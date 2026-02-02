# Experiment Matrix Design

## Objective

Design an experiment matrix that is:
1. **Comprehensive:** Covers key design-space dimensions
2. **Feasible:** Can run on laptop (with longer runtime)
3. **Strong:** Sufficient for Q1/SCIE publication

## Experiment Dimensions

| Dimension | Values | Count | Rationale |
|-----------|--------|-------|-----------|
| **Workload** | MNIST-CNN, CIFAR10-CNN | 2 | Generality across tasks |
| **Data Distribution** | IID, Non-IID (α=0.5) | 2 | FL heterogeneity |
| **Num Clients** | 5, 10 | 2 | Scale effects |
| **Network Profile** | NET0, NET2, NET4 | 3 | Baseline + representative edge |
| **Security Config** | SEC0, SEC1, SEC2, SEC3 | 4 | Design-space knobs |
| **Seeds** | 0, 1, 2, 3, 4 | 5 | Statistical power |

**Total configurations:** 2 × 2 × 2 × 3 × 4 × 5 = **480 runs**

## Three-Tier Experiment Strategy

### Tier 1: Core Set (PRIORITY - Write Draft)

**Purpose:** Get key results FAST for initial paper draft.

**Config:**
- Workload: MNIST-CNN only
- Data: IID + Non-IID
- Clients: 5
- Networks: NET0 (baseline), NET2 (edge)
- Security: SEC0, SEC1, SEC2, SEC3
- Seeds: 5

**Total:** 1 × 2 × 1 × 2 × 4 × 5 = **80 runs**

**Expected runtime:** ~20-40 hours (depending on rounds)

**Deliverable:** Answers RQ1 & RQ2, generates Fig 2-6

---

### Tier 2: Extended Set (STRENGTHEN)

**Purpose:** Add robustness with more conditions.

**Additional configs:**
- Add NET4 (higher impairment)
- Add 10 clients (scale)

**Increment:** 1 × 2 × 2 × 3 × 4 × 5 = **240 runs** (total 320 with Tier 1)

**Expected runtime:** +40-80 hours

**Deliverable:** Strengthens claims, adds ablation studies

---

### Tier 3: Generality Set (OPTIONAL - Enhance Impact)

**Purpose:** Show results generalize to other workloads.

**Additional configs:**
- Add CIFAR10-CNN workload

**Increment:** Full 480 runs

**Deliverable:** Answers "does this apply beyond MNIST?"

---

## Detailed Configuration Tables

### Network Profiles

| Profile | Delay | Jitter | Loss | Bandwidth | Use Case |
|---------|-------|--------|------|-----------|----------|
| **NET0** | 0ms | 0ms | 0% | Unlimited | Datacenter baseline |
| **NET1** | 20ms | 5ms | 0% | Unlimited | Low-latency edge |
| **NET2** | 80ms | 20ms | 0% | Unlimited | Typical edge/4G |
| **NET3** | 0ms | 0ms | 0.5% | Unlimited | Lossy WiFi |
| **NET4** | 50ms | 10ms | 1% | Unlimited | Congested edge |
| **NET5** | 0ms | 0ms | 0% | 10 Mbps | Bandwidth-limited (future work) |

**For Core Set:** Use NET0 (baseline) + NET2 (representative edge)

**For Extended:** Add NET4 (stress test)

### Security Configurations

| Config | NetworkPolicy | mTLS/Mesh | Description |
|--------|--------------|-----------|-------------|
| **SEC0** | Allow-all | Off | Baseline (no security) |
| **SEC1** | Default-deny + allow-list | Off | Network isolation only |
| **SEC2** | Allow-all | On (Linkerd) | mTLS only |
| **SEC3** | Default-deny + allow-list | On | Full zero-trust |

### Workload Details

#### W1: MNIST-CNN

```python
model = nn.Sequential(
    nn.Conv2d(1, 32, 3, 1),
    nn.ReLU(),
    nn.Conv2d(32, 64, 3, 1),
    nn.ReLU(),
    nn.MaxPool2d(2),
    nn.Dropout(0.25),
    nn.Flatten(),
    nn.Linear(9216, 128),
    nn.ReLU(),
    nn.Dropout(0.5),
    nn.Linear(128, 10)
)
```

- **Rounds:** 50
- **Local epochs:** 1
- **Batch size:** 32
- **Learning rate:** 0.01
- **Target accuracy:** 95%, 97%

#### W2: CIFAR10-CNN

```python
model = nn.Sequential(
    nn.Conv2d(3, 32, 3, 1, 1),
    nn.ReLU(),
    nn.MaxPool2d(2),
    nn.Conv2d(32, 64, 3, 1, 1),
    nn.ReLU(),
    nn.MaxPool2d(2),
    nn.Flatten(),
    nn.Linear(64 * 8 * 8, 128),
    nn.ReLU(),
    nn.Linear(128, 10)
)
```

- **Rounds:** 100
- **Local epochs:** 1
- **Batch size:** 32
- **Learning rate:** 0.001
- **Target accuracy:** 60%, 70%

### Data Distribution

**IID:**
- Random split of data across clients
- Each client has balanced classes

**Non-IID (Dirichlet α=0.5):**
- Skewed class distribution using Dirichlet allocation
- Realistic federated setting (clients have different data)

```python
from numpy.random import dirichlet

def create_noniid_split(labels, num_clients, alpha=0.5):
    num_classes = len(np.unique(labels))
    label_distribution = dirichlet([alpha] * num_clients, num_classes)
    # Assign samples based on label_distribution
    return client_indices
```

## Experimental Protocol

### Per-Run Procedure

```
1. Clean K8s cluster state
   - kubectl delete namespace fl-experiment
   - kubectl create namespace fl-experiment

2. Apply security configuration
   - kubectl apply -f k8s/<sec_config>/

3. Apply network profile
   - ./scripts/netem_apply.sh <net_profile>

4. Validate network (30s stabilization)
   - ./scripts/validate_network.sh

5. Deploy FL pods
   - kubectl apply -f k8s/fl-workload.yaml

6. Wait for all pods ready
   - kubectl wait --for=condition=ready pod --all -n fl-experiment

7. Start training (via server trigger)
   - kubectl exec fl-server -- python trigger_training.py

8. Monitor and log
   - kubectl logs -f fl-server > results/raw/<run_id>/server.log &
   - kubectl logs fl-client-* > results/raw/<run_id>/clients.log &

9. Query Prometheus at round boundaries
   - python scripts/query_prometheus.py --run-id <run_id>

10. Training completes (or timeout)

11. Collect final metrics

12. Teardown
    - kubectl delete namespace fl-experiment
    - ./scripts/netem_reset.sh

13. Wait 60s cool-down
```

### Automation Script

`scripts/run_matrix.py`:

```python
import itertools
import subprocess
import time

# Define matrix
workloads = ['mnist']  # Core set
data_dists = ['iid', 'noniid-0.5']
num_clients_list = [5]
networks = ['NET0', 'NET2']
securities = ['SEC0', 'SEC1', 'SEC2', 'SEC3']
seeds = [0, 1, 2, 3, 4]

# Generate all combinations
configs = itertools.product(
    workloads, data_dists, num_clients_list, 
    networks, securities, seeds
)

for config in configs:
    run_id = generate_run_id(*config)
    print(f"Running {run_id}...")
    
    run_single_experiment(
        workload=config[0],
        data_dist=config[1],
        num_clients=config[2],
        network=config[3],
        security=config[4],
        seed=config[5]
    )
    
    time.sleep(60)  # Cool-down
```

## Success Criteria per Run

A run is **valid** if:
- [ ] All expected clients connected to server
- [ ] At least 40/50 rounds completed (MNIST)
- [ ] No Kubernetes pod crashes
- [ ] Prometheus has metrics for ≥90% of rounds
- [ ] Network validation passed

**Invalid runs:** Re-run with same seed (document in notes)

## Data Outputs per Run

```
results/raw/<run_id>/
├── metadata.json          # Run configuration
├── server.log             # FL server logs (JSON lines)
├── clients.log            # All client logs
├── network_validation.txt # ping/iperf results
├── prometheus_metrics.csv # Queried metrics
└── summary.json           # Computed metrics (TTA, p99, etc.)
```

## Analysis Scripts

### 1. Parse logs → summary metrics

`scripts/parse_run.py`:
- Input: `results/raw/<run_id>/`
- Output: `results/processed/<run_id>_summary.csv`
- Computes: TTA, round latencies (p50/p95/p99), bytes/round, failure rate

### 2. Aggregate across repeats

`scripts/aggregate_repeats.py`:
- Input: All runs with same (workload, data, clients, network, security), different seeds
- Output: Mean ± 95% CI for each metric
- Output: `results/processed/aggregated.csv`

### 3. Generate figures

`scripts/generate_figures.py`:
- Input: `results/processed/aggregated.csv`
- Output: `results/figures/fig*.pdf`

## Expected Results (Hypotheses)

Based on prior work, we expect:

1. **SEC1 (NetworkPolicy):** Minimal latency overhead (<5%), possible initial connection delays
2. **SEC2 (mTLS):** 10-20% latency overhead, 5-10% higher CPU usage
3. **SEC3 (Both):** Additive overhead, potential for higher failure rates under NET4
4. **NET2 vs NET0:** 3-4x round latency increase (80ms delay each way)
5. **NET4 (loss):** Higher p99 (due to retries), possible convergence issues

**But:** We don't assume results—measurement will tell us!

## Timeline Estimate

| Phase | Tasks | Duration | Cumulative |
|-------|-------|----------|------------|
| Setup | Install tools, deploy baseline | 3 days | Day 3 |
| Core Set | 80 runs + debugging | 7 days | Day 10 |
| Analysis | Parse, aggregate, initial figures | 4 days | Day 14 |
| **Draft 1** | Write paper with core results | 5 days | Day 19 |
| Extended | +240 runs | 10 days | Day 29 |
| Refinement | More figures, statistics | 4 days | Day 33 |
| **Draft 2** | Complete paper | 5 days | Day 38 |
| Generality | +160 runs (CIFAR) | 7 days | Day 45 |
| **Final** | Polish, proofread | 3 days | Day 48 |

**Total:** ~7 weeks for full Tier 3

**Tier 1 (Core):** ~3 weeks to first draft

## Cost-Benefit Analysis

| Tier | Runs | Runtime | Value |
|------|------|---------|-------|
| Core | 80 | ~30h | **High:** First paper draft, answers main RQs |
| Extended | +240 | +60h | **Medium:** Strengthens claims, more conditions |
| Generality | +160 | +40h | **Low-Medium:** Generality, but diminishing returns |

**Recommendation:** Do Core → Draft → Get feedback → Decide on Extended/Generality

---

**Status:** This matrix is **feasible and strong**. Tier 1 alone is publishable if well-executed.

**Last updated:** 2026-02-02
