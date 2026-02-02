# Getting Started with ZeroTrust-FLBench

## Complete Setup Guide (From Zero to Running Experiments)

This guide will walk you through setting up ZeroTrust-FLBench from scratch and running your first experiments.

### Timeline Overview

- **Day 1:** Setup environment (2-3 hours)
- **Day 2-3:** Run baseline (Milestone 1)
- **Day 4-5:** Add NetworkPolicy (Milestone 2)
- **Week 2:** Run core experiment matrix
- **Week 3:** Analyze results and write draft

---

## Phase 0: Prerequisites (Day 1)

### System Requirements

- **OS:** Ubuntu 20.04/22.04 (or WSL2 with Ubuntu)
- **RAM:** Minimum 8GB, recommended 16GB
- **CPU:** 4+ cores
- **Disk:** 20GB free space
- **Network:** Stable internet for initial downloads

### Install Required Tools

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker  # Or log out and back in

# Verify Docker
docker run hello-world

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
kubectl version --client

# Install minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Verify minikube
minikube version

# Install Python 3.11 (if not already installed)
sudo apt-get install -y python3.11 python3.11-venv python3-pip

# Install git (if needed)
sudo apt-get install -y git
```

### Clone Repository

```bash
cd ~
git clone https://github.com/yourusername/ZeroTrust-FLBench.git
cd ZeroTrust-FLBench
```

### Setup Python Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Start Minikube with Calico CNI

```bash
# Start with Calico (supports NetworkPolicy)
minikube start \
  --cpus=4 \
  --memory=8192 \
  --disk-size=20g \
  --cni=calico \
  --kubernetes-version=v1.28.0

# Verify cluster
kubectl cluster-info
kubectl get nodes
kubectl get pods -A

# Enable metrics-server (for resource monitoring)
minikube addons enable metrics-server
```

**Expected output:** Node should be "Ready", all system pods "Running".

---

## Phase 1: Build and Deploy Baseline FL (Days 2-3)

### Step 1: Build Docker Image

```bash
# Build image
docker build -t zerotrust-flbench:latest .

# Load into minikube
minikube image load zerotrust-flbench:latest

# Verify
minikube image ls | grep zerotrust
```

### Step 2: Deploy Baseline (SEC0, NET0)

```bash
# Deploy FL workload
kubectl apply -f k8s/00-baseline/fl-deployment.yaml

# Check deployment
kubectl get pods -n fl-experiment

# Expected: 1 server pod + 5 client jobs
```

**Wait for pods to be ready:**

```bash
kubectl wait --for=condition=ready pod -l app=fl-server -n fl-experiment --timeout=300s
```

### Step 3: Monitor Training

```bash
# Follow server logs
kubectl logs -n fl-experiment -f deployment/fl-server

# You should see JSON log lines with:
# - "event": "round_start"
# - "event": "round_end"
# - "test_accuracy": ...
```

**Expected behavior:**
- 50 rounds complete
- Accuracy increases from ~10% → 95%+
- Each round takes ~30-60 seconds (NET0, no impairment)

### Step 4: Collect Baseline Results

```bash
# Create results directory
mkdir -p results/raw/baseline_run1

# Collect logs
kubectl logs -n fl-experiment deployment/fl-server > results/raw/baseline_run1/server.log

# Collect client logs
for i in {0..4}; do
  kubectl logs -n fl-experiment job/fl-client-$i >> results/raw/baseline_run1/clients.log
done

# Save metadata
cat > results/raw/baseline_run1/metadata.json <<EOF
{
  "run_id": "baseline_run1",
  "timestamp": "$(date -Iseconds)",
  "config": {
    "security": "SEC0",
    "network": "NET0",
    "num_clients": 5,
    "data_distribution": "iid",
    "seed": 42
  }
}
EOF
```

### Step 5: Verify Results

```bash
# Parse accuracy from logs
grep "test_accuracy" results/raw/baseline_run1/server.log | tail -10

# Check if target accuracy reached
grep "target_accuracy_reached" results/raw/baseline_run1/server.log
```

**Success criteria for Milestone 1:**
- ✅ Training completes 50 rounds
- ✅ Accuracy reaches 95%+
- ✅ Logs contain structured JSON events
- ✅ No pod crashes or errors

---

## Phase 2: Add Network Emulation (Day 4)

### Step 1: Test Network Scripts

```bash
# Make scripts executable
chmod +x scripts/netem_apply.sh
chmod +x scripts/netem_reset.sh

# Apply NET2 profile (80ms delay, 20ms jitter)
./scripts/netem_apply.sh NET2
```

### Step 2: Validate Network Conditions

```bash
# From a client pod, ping the server
kubectl exec -n fl-experiment job/fl-client-0 -- ping -c 10 fl-server

# Expected: ~160ms RTT (80ms each way)
```

### Step 3: Run Baseline with NET2

```bash
# Clean up previous run
kubectl delete namespace fl-experiment
kubectl create namespace fl-experiment

# Deploy
kubectl apply -f k8s/00-baseline/fl-deployment.yaml

# Wait and monitor
kubectl logs -n fl-experiment -f deployment/fl-server
```

**Expected behavior:**
- Round latency increases ~3-4x (due to 160ms RTT)
- Still converges to 95%+, just slower

### Step 4: Reset Network

```bash
./scripts/netem_reset.sh

# Verify reset
minikube ssh "sudo tc qdisc show"
# Should show: qdisc noqueue (no netem)
```

---

## Phase 3: Add NetworkPolicy (Days 5-6)

### Step 1: Apply SEC1 (NetworkPolicy)

```bash
# Clean cluster
kubectl delete namespace fl-experiment
kubectl create namespace fl-experiment

# Deploy baseline
kubectl apply -f k8s/00-baseline/fl-deployment.yaml

# Apply NetworkPolicy
kubectl apply -f k8s/10-networkpolicy/networkpolicies.yaml

# Check policies
kubectl get networkpolicies -n fl-experiment
```

### Step 2: Verify Policies Work

```bash
# Wait for pods
kubectl wait --for=condition=ready pod -l app=fl-server -n fl-experiment --timeout=300s

# Test connectivity
# Client → Server (should work)
kubectl exec -n fl-experiment job/fl-client-0 -- nc -zv fl-server 8080

# Expected: Connection succeeded

# Client → Another Client (should fail)
kubectl exec -n fl-experiment job/fl-client-0 -- nc -zv fl-client-1 8080

# Expected: Timeout or connection refused
```

### Step 3: Monitor Training with NetworkPolicy

```bash
kubectl logs -n fl-experiment -f deployment/fl-server
```

**Common issues to watch for:**
- DNS resolution failures → Check DNS policy
- Connection timeouts → Check egress rules
- Metrics scraping blocked → Add Prometheus ingress rule

### Step 4: Collect SEC1 Results

```bash
mkdir -p results/raw/sec1_net0_run1
kubectl logs -n fl-experiment deployment/fl-server > results/raw/sec1_net0_run1/server.log
```

**Success criteria for Milestone 2:**
- ✅ NetworkPolicy applied without breaking FL
- ✅ Training still completes
- ✅ Similar performance to SEC0 under NET0

---

## Phase 4: Run Core Experiment Matrix (Week 2)

### Step 1: Review Experiment Plan

```bash
# See experiment matrix
cat docs/experiment_matrix.md

# Dry run to see all configs
python scripts/run_matrix.py --tier core --dry-run
```

**Core set:** 80 runs (MNIST, IID+NonIID, 5 clients, NET0+NET2, SEC0-SEC3, 5 seeds)

**Estimated time:** 30-40 hours

### Step 2: Start Automated Runs

```bash
# Activate venv
source venv/bin/activate

# Run core matrix
python scripts/run_matrix.py --tier core --results-dir results/raw

# Monitor progress
# The script will:
# - Clean namespace between runs
# - Apply network profile
# - Apply security config
# - Wait for training
# - Collect logs
# - Move to next config
```

**Tips:**
- Run overnight or over weekend
- Use `tmux` or `screen` to keep session alive
- Check logs periodically: `tail -f results/raw/latest_run/server.log`

### Step 3: Handle Failures

If a run fails:

```bash
# Resume from specific experiment number
python scripts/run_matrix.py --tier core --resume-from 15
```

---

## Phase 5: Analyze Results (Week 3)

### Step 1: Parse Logs

```bash
# Create analysis notebook
jupyter notebook

# Or use provided parser script
python scripts/parse_logs.py --input results/raw/ --output results/processed/
```

### Step 2: Generate Summary

For each run, extract:
- Time-to-target-accuracy (TTA)
- Round latency distribution (p50/p95/p99)
- Bytes per round
- Failure rate

### Step 3: Create Figures

Key figures to generate:

1. **Heatmap:** p99 latency across (SEC × NET)
2. **ECDF:** Round latency distribution
3. **Bar chart:** TTA with error bars
4. **Line plot:** Accuracy convergence over rounds

---

## Quick Commands Cheat Sheet

```bash
# Start minikube
minikube start --cpus=4 --memory=8192 --cni=calico

# Deploy baseline
kubectl apply -f k8s/00-baseline/fl-deployment.yaml

# Apply NetworkPolicy
kubectl apply -f k8s/10-networkpolicy/networkpolicies.yaml

# Apply network emulation
./scripts/netem_apply.sh NET2

# Reset network
./scripts/netem_reset.sh

# View logs
kubectl logs -n fl-experiment -f deployment/fl-server

# Clean up
kubectl delete namespace fl-experiment

# Stop minikube
minikube stop
```

---

## Troubleshooting

### Issue: Pods stuck in "Pending"

**Cause:** Insufficient resources.

**Fix:**
```bash
minikube delete
minikube start --cpus=4 --memory=8192
```

### Issue: DNS not working with NetworkPolicy

**Symptom:** Clients can't resolve `fl-server`.

**Fix:** Ensure DNS egress rule allows kube-system namespace.

```bash
kubectl get networkpolicy -n fl-experiment allow-dns -o yaml
```

### Issue: Network emulation not applying

**Fix:**
```bash
# Check if tc is working
minikube ssh "sudo tc qdisc show"

# Manually test
minikube ssh "sudo tc qdisc add dev eth0 root netem delay 80ms"
```

### Issue: Image not found

**Fix:**
```bash
# Rebuild and reload
docker build -t zerotrust-flbench:latest .
minikube image load zerotrust-flbench:latest
```

---

## Next Steps

After completing the core experiments:

1. **Extend:** Run extended matrix (add NET4, 10 clients)
2. **Generality:** Add CIFAR-10 workload
3. **mTLS:** Install Linkerd and test SEC2/SEC3
4. **Analysis:** Generate all figures
5. **Write:** Draft paper with results

---

## Additional Resources

- **Flower docs:** https://flower.ai/docs/
- **NetworkPolicy guide:** https://kubernetes.io/docs/concepts/services-networking/network-policies/
- **Linkerd docs:** https://linkerd.io/2/getting-started/
- **netem docs:** `man tc-netem`

---

**Last updated:** 2026-02-02
