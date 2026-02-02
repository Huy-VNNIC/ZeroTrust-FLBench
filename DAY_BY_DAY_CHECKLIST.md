# 7-Day Checklist: From Fixed Code → 80-Run Core Matrix

**Environment:** Linux (Ubuntu), minikube, Linkerd  
**Goal:** Core matrix (80 runs) + 6 publication figures ready

---

## 📅 Day 1: Mốc 0 - Chạy được 1 run SEC0+NET0 (Baseline)

### Morning Session (3 hours)

#### ✅ 1.1.1 Build Docker Image
```bash
cd /home/dtu/ZeroTrust-FLBench

# Build image
docker build -t zerotrust-flbench:latest .

# Verify image
docker images | grep zerotrust
# Expected: zerotrust-flbench   latest   <image_id>   <size>
```

**Tick khi:** Image build thành công, không có errors.

#### ✅ 1.1.2 Test Local (No K8s) - Optional but Recommended
```bash
# Test server locally
docker run --rm \
  -v /tmp/mnist:/data/mnist \
  zerotrust-flbench:latest \
  python /app/src/fl_server.py --help

# Expected: Show help message with --num-rounds, --min-fit-clients, etc.
```

**Tick khi:** Help message hiển thị đúng.

#### ✅ 1.1.3 Load Image vào Minikube
```bash
# Start minikube (if not running)
minikube status || minikube start --cpus=4 --memory=8192 --driver=docker

# Load image
minikube image load zerotrust-flbench:latest

# Verify
minikube image ls | grep zerotrust
# Expected: docker.io/library/zerotrust-flbench:latest
```

**Tick khi:** Image có trong minikube.

---

### Afternoon Session (3 hours)

#### ✅ 1.2.1 Run First Experiment (SEC0+NET0+IID)
```bash
# Run với 10 rounds (test nhanh trước)
./scripts/run_one.py \
  --sec-level SEC0 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 10 \
  --iid \
  --data-seed 42 \
  --output-dir results/raw

# Wait 5-10 minutes...
```

**Expected output:**
```json
{"event": "experiment_success", "run_id": "SEC0_NET0_1738598400"}
```

**Tick khi:** 
- Experiment completes successfully
- No pod crashes/restarts

#### ✅ 1.2.2 Inspect Logs
```bash
# Find latest run_id
RUN_ID=$(ls -t results/raw/ | head -1)
echo "Latest run: $RUN_ID"

# Check server log
cat results/raw/$RUN_ID/server_${RUN_ID}.log | jq '.event' | sort | uniq -c

# Expected events:
#   1 server_start
#  10 round_start
#  10 round_end
#   1 server_end
```

**Tick khi:**
- Server log có đủ events
- Client logs có `fit_start`, `fit_end`
- RUN_ID xuất hiện trong mọi log entry

#### ✅ 1.2.3 Validate Accuracy
```bash
# Extract final accuracy
cat results/raw/$RUN_ID/server_${RUN_ID}.log | \
  jq 'select(.event == "round_complete" and .round == 10) | .test_accuracy'

# Expected: 0.90 - 0.95 (90-95% for MNIST IID)
```

**Tick khi:** Accuracy > 0.85 (reasonable convergence).

---

### Evening: Extend to 50 Rounds (Mốc 0 Checkpoint)

#### ✅ 1.3.1 Run Full 50 Rounds
```bash
./scripts/run_one.py \
  --sec-level SEC0 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 50 \
  --iid \
  --data-seed 42 \
  --output-dir results/raw

# Duration: ~20-30 minutes
```

**Tick khi:**
- 50 rounds complete
- Final accuracy > 0.92
- No OOM/crashes

#### ✅ 1.3.2 Archive as Baseline
```bash
RUN_ID=$(ls -t results/raw/ | head -1)
mkdir -p results/baseline
cp -r results/raw/$RUN_ID results/baseline/SEC0_NET0_50rounds

echo "✅ Mốc 0 đạt: SEC0 NET0 50 rounds hoàn thành"
```

---

## 📅 Day 2: Parser + Sanity Plots

### Morning Session (4 hours)

#### ✅ 2.1.1 Test Parser Script
```bash
# Parse baseline run
python scripts/parse_logs.py \
  --log-dir results/baseline/SEC0_NET0_50rounds \
  --output-dir results/processed

# Verify outputs
ls -lh results/processed/
# Expected:
#   rounds.csv
#   clients.csv
#   summary.csv
```

**Check rounds.csv:**
```bash
head -5 results/processed/rounds.csv
# Expected columns: run_id,round_id,start_ts,end_ts,duration,accuracy,loss,failures
```

**Tick khi:** CSV files có đúng cột và 50 rows (rounds.csv).

#### ✅ 2.1.2 Inspect Summary Stats
```bash
cat results/processed/summary.csv | column -t -s,

# Expected 1 row with:
# - tta_95, tta_97 (time to 95%/97% accuracy)
# - p50_round, p95_round, p99_round (latency percentiles)
# - failure_rate = 0
```

**Tick khi:** Summary có đầy đủ metrics và reasonable values.

---

### Afternoon Session (3 hours)

#### ✅ 2.2.1 Generate Sanity Plots
```bash
python scripts/plot_sanity.py \
  --rounds-csv results/processed/rounds.csv \
  --output-dir results/figures/sanity

# Verify plots
ls -lh results/figures/sanity/
# Expected:
#   accuracy_vs_round.png
#   duration_vs_round.png
#   ecdf_duration.png
```

**Open plots and validate:**
```bash
# View plots (use eog, feh, or copy to host)
eog results/figures/sanity/accuracy_vs_round.png &
eog results/figures/sanity/duration_vs_round.png &
eog results/figures/sanity/ecdf_duration.png &
```

**Tick khi:**
- Accuracy tăng dần (monotonic or near-monotonic)
- Duration không có outliers vô lý (>5x median)
- ECDF smooth, p95/p99 visible

#### ✅ 2.2.2 Sanity Check: Reproducibility
```bash
# Run 2nd time with same seed
./scripts/run_one.py \
  --sec-level SEC0 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 10 \
  --iid \
  --data-seed 42 \
  --output-dir results/raw

# Compare final accuracies
RUN1=$(ls -t results/raw/ | sed -n 2p)  # Previous run
RUN2=$(ls -t results/raw/ | sed -n 1p)  # Latest run

ACC1=$(cat results/raw/$RUN1/server*.log | jq -s 'last | .test_accuracy')
ACC2=$(cat results/raw/$RUN2/server*.log | jq -s 'last | .test_accuracy')

echo "Run 1: $ACC1, Run 2: $ACC2"
# Expected: Difference < 0.005 (0.5%)
```

**Tick khi:** Accuracy reproducible trong 0.5%.

---

## 📅 Day 3: Security Configs (SEC1, SEC2, SEC3)

### Morning: SEC1 (NetworkPolicy)

#### ✅ 3.1.1 Review NetworkPolicy Config
```bash
cat k8s/10-networkpolicy/networkpolicies.yaml

# Verify:
# - default-deny-all exists
# - allow-fl-traffic allows port 8080
```

#### ✅ 3.1.2 Run SEC1 Experiment
```bash
./scripts/run_one.py \
  --sec-level SEC1 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 10 \
  --iid \
  --data-seed 42 \
  --output-dir results/raw
```

**Tick khi:**
- Experiment completes (no DNS/connection errors)
- Accuracy similar to SEC0 (±2%)

#### ✅ 3.1.3 Compare SEC0 vs SEC1
```bash
# Parse both runs
python scripts/compare_runs.py \
  --run1 results/baseline/SEC0_NET0_50rounds \
  --run2 results/raw/SEC1_NET0_<timestamp> \
  --output results/processed/sec0_vs_sec1.txt

# Check latency increase
cat results/processed/sec0_vs_sec1.txt | grep "p95_latency_increase"
# Expected: 5-15% increase
```

**Tick khi:** SEC1 overhead quantified and reasonable.

---

### Afternoon: SEC2 (mTLS/Linkerd)

#### ✅ 3.2.1 Install Linkerd
```bash
# Install Linkerd CLI
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh
export PATH=$PATH:$HOME/.linkerd2/bin

# Verify
linkerd version
# Expected: Client version: stable-2.14.x

# Pre-check
linkerd check --pre
# Expected: All checks pass ✔
```

#### ✅ 3.2.2 Install Linkerd Control Plane
```bash
# Install CRDs
linkerd install --crds | kubectl apply -f -

# Install control plane
linkerd install | kubectl apply -f -

# Wait for ready
linkerd check
# Expected: All checks pass ✔ (may take 2-3 mins)
```

**Tick khi:** `linkerd check` all green.

#### ✅ 3.2.3 Enable Auto-Injection
```bash
# Annotate namespace
kubectl annotate namespace fl-experiment linkerd.io/inject=enabled

# Verify
kubectl get namespace fl-experiment -o yaml | grep inject
# Expected: linkerd.io/inject: enabled
```

#### ✅ 3.2.4 Run SEC2 Experiment
```bash
./scripts/run_one.py \
  --sec-level SEC2 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 10 \
  --iid \
  --data-seed 42 \
  --output-dir results/raw

# During run, check sidecar injection:
kubectl get pods -n fl-experiment
# Expected: 2/2 READY (app container + linkerd-proxy)
```

**Tick khi:**
- Pods have sidecars
- Experiment completes
- Accuracy similar to SEC0

---

### Evening: SEC3 (NetworkPolicy + mTLS) - The Hard One

#### ✅ 3.3.1 Update NetworkPolicy for Linkerd
```bash
# Add Linkerd proxy ports to NetworkPolicy
# Already done in k8s/25-combined/ (we'll create this)
```

#### ✅ 3.3.2 Create SEC3 Manifests
```bash
# Copy SEC1 base
cp -r k8s/10-networkpolicy k8s/25-combined

# Edit networkpolicies.yaml to allow Linkerd proxy
nano k8s/25-combined/networkpolicies.yaml

# Add to allow-fl-traffic ingress:
#   - protocol: TCP
#     port: 4143  # Linkerd inbound proxy
```

#### ✅ 3.3.3 Run SEC3 Experiment
```bash
./scripts/run_one.py \
  --sec-level SEC3 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 10 \
  --iid \
  --data-seed 42 \
  --output-dir results/raw
```

**Tick khi:** SEC3 completes successfully (này là **mốc kỹ thuật lớn**!).

---

## 📅 Day 4: Network Emulation (NET0/NET2/NET4)

### Morning: Netem Scripts

#### ✅ 4.1.1 Verify Netem Scripts
```bash
cat scripts/netem_apply.sh
cat scripts/netem_reset.sh

# Make executable
chmod +x scripts/netem_apply.sh scripts/netem_reset.sh
```

#### ✅ 4.1.2 Test Netem Manually
```bash
# Start SEC0 experiment (don't wait for completion)
./scripts/run_one.py \
  --sec-level SEC0 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 50 \
  --iid \
  --data-seed 42 \
  --output-dir results/raw &

# Wait for pods to spawn
sleep 30

# Apply NET2 profile to one client
./scripts/netem_apply.sh fl-experiment fl-client-1 NET2

# Verify tc rules
kubectl exec -n fl-experiment fl-client-1 -- tc qdisc show
# Expected: netem delay 50ms ...

# Reset after experiment
./scripts/netem_reset.sh fl-experiment fl-client-1
```

**Tick khi:** tc rules apply correctly.

---

### Afternoon: Network Profile Validation

#### ✅ 4.2.1 Create Network Validation Script
```bash
# Create scripts/validate_network.sh
# (Already in TODO)
```

#### ✅ 4.2.2 Run Experiments with Different Networks
```bash
# NET0 (baseline)
./scripts/run_one.py \
  --sec-level SEC0 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 10

# NET2 (WiFi edge)
./scripts/run_one.py \
  --sec-level SEC0 \
  --net-profile NET2 \
  --num-clients 5 \
  --num-rounds 10

# NET4 (congested edge)
./scripts/run_one.py \
  --sec-level SEC0 \
  --net-profile NET4 \
  --num-clients 5 \
  --num-rounds 10
```

#### ✅ 4.2.3 Compare Network Impact
```bash
# Parse all 3 runs
python scripts/parse_logs.py \
  --log-dir results/raw \
  --output-dir results/processed

# Compare p95 latencies
cat results/processed/summary.csv | grep "SEC0" | column -t -s,

# Expected trend: NET0 < NET2 < NET4
```

**Tick khi:** Latency increases with network degradation.

---

## 📅 Day 5: Automate Core Matrix Runner

### Morning: Build run_matrix.py

#### ✅ 5.1.1 Update run_matrix.py
```bash
# Test dry-run first
python scripts/run_matrix.py \
  --sec-levels SEC0,SEC1 \
  --net-profiles NET0,NET2 \
  --iid \
  --seeds 0,1 \
  --num-clients 5 \
  --num-rounds 10 \
  --output-dir results/core_matrix \
  --dry-run

# Expected: Print 8 configs (2 SEC × 2 NET × 1 IID × 2 seeds)
```

**Tick khi:** Dry-run shows correct config count.

---

### Afternoon: Pilot Matrix (Small Scale)

#### ✅ 5.1.2 Run Pilot Matrix (16 runs)
```bash
# 2 SEC × 2 NET × 2 IID × 2 seeds = 16 runs
python scripts/run_matrix.py \
  --sec-levels SEC0,SEC1 \
  --net-profiles NET0,NET2 \
  --iid \
  --noniid \
  --alpha 0.5 \
  --seeds 0,1 \
  --num-clients 5 \
  --num-rounds 10 \
  --output-dir results/pilot_matrix \
  --checkpoint results/pilot_checkpoint.json

# Duration: ~5-6 hours (20min/run × 16)
# Run overnight if needed
```

**Tick khi:**
- All 16 runs complete
- `results/pilot_matrix/summary.csv` has 16 rows
- No more than 1-2 failures

---

### Evening: Quality Check

#### ✅ 5.2.1 Check Failed Runs
```bash
cat results/pilot_checkpoint.json | jq '.failed_runs'

# If any failures, inspect logs
```

#### ✅ 5.2.2 Rerun Failed Configs
```bash
# run_matrix.py automatically retries with --max-retries 3
# But manual rerun if needed:
./scripts/run_one.py \
  --sec-level SEC0 \
  --net-profile NET2 \
  --num-clients 5 \
  --num-rounds 10 \
  --iid \
  --data-seed 42
```

**Tick khi:** Failure rate < 5%.

---

## 📅 Day 6: Full Core Matrix (80 Runs)

### Setup: Start Core Matrix

#### ✅ 6.1 Run Full Matrix
```bash
# 4 SEC × 2 NET × 2 IID × 5 seeds = 80 runs
python scripts/run_matrix.py \
  --sec-levels SEC0,SEC1,SEC2,SEC3 \
  --net-profiles NET0,NET2 \
  --iid \
  --noniid \
  --alpha 0.5 \
  --seeds 0,1,2,3,4 \
  --num-clients 5 \
  --num-rounds 50 \
  --output-dir results/core_matrix \
  --checkpoint results/core_checkpoint.json \
  --max-retries 3

# Duration: ~27-40 hours (20-30min/run × 80)
# Run in screen/tmux:
screen -S fl-matrix
python scripts/run_matrix.py ...
# Ctrl+A D to detach
```

#### ✅ 6.2 Monitor Progress
```bash
# Check checkpoint
watch -n 60 "cat results/core_checkpoint.json | jq '.completed_runs | length'"

# Check pod status
watch -n 30 "kubectl get pods -n fl-experiment"

# Check logs
tail -f results/core_matrix/matrix.log
```

**Tick khi:** Matrix runner starts and checkpoint updates.

---

### Day 6-7: Wait for Completion + Monitor

**Actions:**
- Check progress every few hours
- Restart if minikube crashes
- Resume from checkpoint

**Tick khi:** 80/80 runs complete (or 75+/80 with acceptable failures).

---

## 📅 Day 7: Analysis + Paper Figures

### Morning: Parse All Logs

#### ✅ 7.1.1 Parse Core Matrix Results
```bash
python scripts/parse_logs.py \
  --log-dir results/core_matrix \
  --output-dir results/processed

# Verify summary
wc -l results/processed/summary.csv
# Expected: 81 lines (1 header + 80 runs)
```

#### ✅ 7.1.2 Compute Statistics
```bash
python scripts/compute_stats.py \
  --input results/processed/summary.csv \
  --output results/processed/statistics.csv

# Check stats
head results/processed/statistics.csv
```

**Tick khi:** Statistics computed for all configs.

---

### Afternoon: Generate 6 Main Figures

#### ✅ 7.2.1 Generate Publication Figures
```bash
python scripts/plot_results.py \
  --summary-csv results/processed/summary.csv \
  --output-dir results/figures/publication

# Expected outputs:
ls results/figures/publication/
#   fig1_heatmap_p99_iid.png
#   fig2_heatmap_p99_noniid.png
#   fig3_ecdf_latency.png
#   fig4_tta_comparison.png
#   fig5_failure_rate.png
#   fig6_overhead.png
```

#### ✅ 7.2.2 Visual Inspection
```bash
# Open all figures
eog results/figures/publication/*.png &
```

**Quality checks:**
- Heatmaps show clear trends (NET2 > NET0)
- ECDFs are smooth
- Error bars (95% CI) visible
- Labels/legends clear

**Tick khi:** All 6 figures publication-ready.

---

### Evening: Package Results

#### ✅ 7.3.1 Create Results Archive
```bash
tar -czf results-core-matrix.tar.gz \
  results/processed/ \
  results/figures/ \
  results/core_checkpoint.json

# Verify
ls -lh results-core-matrix.tar.gz
# Expected: ~50-100 MB
```

#### ✅ 7.3.2 Generate Summary Report
```bash
python scripts/generate_report.py \
  --summary-csv results/processed/summary.csv \
  --output results/REPORT.md

# Review
cat results/REPORT.md
```

**Tick khi:**
- Report has key findings
- Statistics with confidence intervals
- Tables ready for paper

---

## 🎯 Day 7 End: What You Should Have

### Files Ready:
- ✅ `results/processed/summary.csv` (80 rows)
- ✅ `results/figures/publication/` (6 figures)
- ✅ `results/REPORT.md` (summary statistics)
- ✅ `results-core-matrix.tar.gz` (archive)

### Metrics Confirmed:
- ✅ TTA increases: NET0 < NET2
- ✅ Latency overhead: SEC0 < SEC1 < SEC2 < SEC3
- ✅ Failure rate < 5%
- ✅ IID vs Non-IID trends visible

### Ready for Paper:
- ✅ Results section (can draft in 1 day)
- ✅ Methodology section (describe matrix)
- ✅ Figures with clear trends

---

## 🚨 Troubleshooting Checklist

### If Experiment Hangs:
```bash
# Check pod status
kubectl get pods -n fl-experiment

# Check logs
kubectl logs -n fl-experiment <pod-name>

# If stuck, delete and rerun
kubectl delete namespace fl-experiment
# Runner will resume from checkpoint
```

### If Accuracy Too Low:
```bash
# Check data split
python scripts/validate_splits.py --num-clients 5 --data-seed 42

# Increase rounds
# Edit run_matrix.py: --num-rounds 100
```

### If Too Many Failures:
```bash
# Check minikube resources
minikube status

# Increase resources
minikube delete
minikube start --cpus=8 --memory=16384

# Reload image
minikube image load zerotrust-flbench:latest
```

### If Checkpoint Corrupted:
```bash
# Backup
cp results/core_checkpoint.json results/core_checkpoint.json.bak

# Reset specific run
jq '.failed_runs = []' results/core_checkpoint.json > tmp.json
mv tmp.json results/core_checkpoint.json
```

---

## 📊 Success Criteria Summary

| Criterion | Target | How to Verify |
|-----------|--------|---------------|
| Day 1 Complete | SEC0+NET0 50 rounds | Accuracy > 0.92 |
| Sanity Plots OK | No outliers | Visual inspection |
| SEC3 Working | All security levels | Experiment completes |
| Network Trends | NET0 < NET2 < NET4 | p95 latency ordering |
| Core Matrix | 80/80 or 75+/80 | `wc -l summary.csv` |
| Figures Ready | 6 publication plots | Visual quality check |
| Stats Computed | CI, p-values | REPORT.md generated |

---

## 🎓 After Day 7: Next Steps

1. **Week 2:** Draft Results + Methodology sections
2. **Week 3:** Add Introduction + Related Work
3. **Week 4:** Full draft review + internal feedback
4. **Week 5-6:** Extend matrix (optional: NET4, CIFAR-10)
5. **Week 7-8:** Paper polishing + figures refinement
6. **Week 9:** Submit to DCN

---

**Bây giờ bạn có thể bắt đầu Day 1! Tick từng box và báo lại khi đạt Mốc 0. 🚀**
