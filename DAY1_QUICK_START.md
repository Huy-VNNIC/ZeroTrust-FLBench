# Day 1 Quick Start: Mốc 0 Checklist

**Goal:** Chạy được SEC0+NET0 50 rounds sạch + parser + 3 sanity plots

**Time:** 3-4 hours

---

## ⚠️ CRITICAL: 3 Things to Lock Before Running

### ✅ 1. Log Schema Frozen
**Events in code:**
- Server: `experiment_start`, `round_start`, `round_end`, `target_accuracy_reached`, `experiment_end`
- Client: `client_start`, `data_loaded`, `client_init`, `fit_start`, `fit_end`, `client_end`

**Parser updated:** `scripts/parse_logs.py` now parses correct events.

### ✅ 2. Metadata.json Auto-Generated
**run_one.py now creates:**
```
results/raw/<RUN_ID>/
├── server_<RUN_ID>.log
├── fl-client-1_<RUN_ID>.log
├── ...
└── meta.json  # NEW: config, versions, git commit
```

### ✅ 3. Dataset Caching
**Current issue:** MNIST downloads inside pods → network variance.

**Quick fix (for Day 1):** Accept variance, measure later.

**Proper fix (Day 2+):** Use hostPath volume or pre-download.

---

## 📋 Checklist

### Morning Session (2 hours)

#### ☐ Step 1: Build Docker Image (15 min)
```bash
cd /home/dtu/ZeroTrust-FLBench

# Build
docker build -t zerotrust-flbench:latest .

# Verify
docker images | grep zerotrust
```

**Expected:**
```
zerotrust-flbench   latest   abc123...   2.1GB
```

**If fails:** Check `requirements.txt` and `Dockerfile`.

---

#### ☐ Step 2: Load Image to Minikube (5 min)
```bash
# Start minikube (if not running)
minikube status || minikube start --cpus=4 --memory=8192 --driver=docker

# Load image
minikube image load zerotrust-flbench:latest

# Verify
minikube image ls | grep zerotrust
```

**Expected:**
```
docker.io/library/zerotrust-flbench:latest
```

---

#### ☐ Step 3: Test Run (10 rounds) - Catch Errors Early (20 min)
```bash
# Run 10 rounds first
./scripts/run_one.py \
  --sec-level SEC0 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 10 \
  --iid \
  --data-seed 42 \
  --output-dir results/raw

# Duration: 5-10 minutes
```

**Monitor:**
```bash
# Watch pods
watch -n 5 'kubectl get pods -n fl-experiment'

# Check logs (if stuck)
kubectl logs -n fl-experiment -l app=fl-server --tail=20
```

**Expected:**
- Pods: `2/2 READY` (if Linkerd injected) or `1/1 READY`
- Duration: 5-10 min
- Exit: `{"event": "experiment_success", "run_id": "SEC0_NET0_..."}`

**If fails:**
```bash
# Check image exists
minikube image ls | grep zerotrust

# Check pod errors
kubectl describe pod -n fl-experiment <pod-name>

# Check logs
kubectl logs -n fl-experiment <pod-name>

# Common issues:
# - ImagePullBackOff: Image not loaded
# - CrashLoopBackOff: Python error (check logs)
# - Pending: Resource limits too high
```

---

#### ☐ Step 4: Inspect Logs (10 min)
```bash
# Find run directory
RUN_ID=$(ls -t results/raw/ | head -1)
echo "Latest run: $RUN_ID"

# Check structure
ls -lh results/raw/$RUN_ID/
```

**Expected files:**
```
server_SEC0_NET0_<timestamp>.log
fl-client-1_SEC0_NET0_<timestamp>.log
fl-client-2_SEC0_NET0_<timestamp>.log
fl-client-3_SEC0_NET0_<timestamp>.log
fl-client-4_SEC0_NET0_<timestamp>.log
fl-client-5_SEC0_NET0_<timestamp>.log
meta.json  # NEW!
```

**Check meta.json:**
```bash
cat results/raw/$RUN_ID/meta.json | jq .

# Expected:
{
  "run_id": "SEC0_NET0_...",
  "timestamp": "2026-02-02T...",
  "config": {
    "sec_level": "SEC0",
    "net_profile": "NET0",
    ...
  },
  "versions": {
    "git_commit": "29eb66e...",
    "flwr": "1.7.0",
    ...
  }
}
```

---

#### ☐ Step 5: Validate Events in Logs (10 min)
```bash
# Count events in server log
cat results/raw/$RUN_ID/server_*.log | jq '.event' | sort | uniq -c

# Expected for 10 rounds:
#   1 experiment_start
#  10 round_start
#  10 round_end
#   X target_accuracy_reached (0-2 times)
#   1 experiment_end
```

**Check accuracy progression:**
```bash
cat results/raw/$RUN_ID/server_*.log | \
  jq 'select(.event == "round_end") | {round: .round, acc: .test_accuracy}'

# Expected: accuracy increases (0.85 → 0.92+)
```

**If accuracy low (<0.80):**
```bash
# Validate data splits
python scripts/validate_splits.py --num-clients 5 --data-seed 42
```

---

### Lunch Break 🍜

---

### Afternoon Session (1.5 hours)

#### ☐ Step 6: Run Mốc 0 (50 rounds) - The Real Baseline (30 min)
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
# Go for coffee ☕
```

**Success criteria:**
- All 50 rounds complete
- Final accuracy > 0.92
- No pod restarts
- No OOM kills

**Check final accuracy:**
```bash
RUN_ID=$(ls -t results/raw/ | head -1)
cat results/raw/$RUN_ID/server_*.log | \
  jq 'select(.event == "round_end" and .round == 50) | .test_accuracy'

# Expected: 0.92 - 0.95
```

---

#### ☐ Step 7: Archive as Baseline (2 min)
```bash
RUN_ID=$(ls -t results/raw/ | head -1)
mkdir -p results/baseline
cp -r results/raw/$RUN_ID results/baseline/SEC0_NET0_50rounds

echo "✅ Baseline archived: results/baseline/SEC0_NET0_50rounds"
```

---

#### ☐ Step 8: Parse Logs to CSV (5 min)
```bash
python scripts/parse_logs.py \
  --log-dir results/baseline/SEC0_NET0_50rounds \
  --output-dir results/processed

# Verify outputs
ls -lh results/processed/
```

**Expected files:**
```
rounds.csv     # 50 rows (1 per round)
clients.csv    # 250 rows (5 clients × 50 rounds)
summary.csv    # 1 row (aggregate metrics)
```

**Inspect summary:**
```bash
cat results/processed/summary.csv | column -t -s,

# Expected columns:
# run_id, sec_level, net_profile, iid, data_seed, num_rounds,
# final_accuracy, tta_95, tta_97, p50_round, p95_round, p99_round,
# mean_round, std_round, failure_rate
```

---

#### ☐ Step 9: Generate Sanity Plots (10 min)
```bash
python scripts/plot_sanity.py \
  --rounds-csv results/processed/rounds.csv \
  --output-dir results/figures/sanity

# Verify outputs
ls -lh results/figures/sanity/
```

**Expected plots:**
```
accuracy_vs_round.png
duration_vs_round.png
ecdf_duration.png
```

**Visual inspection:**
```bash
# Open plots (adjust command for your system)
eog results/figures/sanity/*.png &
# Or copy to host and view
```

**Quality checks:**
- [ ] Accuracy increases (mostly monotonic)
- [ ] Duration stable (no >5x median outliers)
- [ ] ECDF smooth (no sudden jumps)

**If plots "kỳ" (weird):**
```bash
# Debug specific rounds
cat results/processed/rounds.csv | grep "<problematic_round>"

# Check client logs for that round
grep "round_id.*<N>" results/baseline/SEC0_NET0_50rounds/fl-client-*.log
```

---

### Evening: Reproducibility Test (Optional but Recommended)

#### ☐ Step 10: Run 2nd Time with Same Seed (30 min)
```bash
./scripts/run_one.py \
  --sec-level SEC0 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 10 \
  --iid \
  --data-seed 42 \
  --output-dir results/raw
```

**Compare final accuracies:**
```bash
# Get last 2 runs
RUN1=$(ls -t results/raw/ | sed -n 2p)
RUN2=$(ls -t results/raw/ | sed -n 1p)

ACC1=$(cat results/raw/$RUN1/server_*.log | jq -s 'map(select(.event == "round_end" and .round == 10)) | last | .test_accuracy')
ACC2=$(cat results/raw/$RUN2/server_*.log | jq -s 'map(select(.event == "round_end" and .round == 10)) | last | .test_accuracy')

echo "Run 1: $ACC1"
echo "Run 2: $ACC2"

# Expected: Difference < 0.005 (0.5%)
python3 -c "print('Diff:', abs($ACC1 - $ACC2))"
```

---

## 🎉 Mốc 0 Đạt Khi:

- [x] **Image:** Built and loaded to minikube
- [x] **10-round test:** Completes successfully
- [x] **50-round baseline:** Final accuracy > 0.92
- [x] **Logs:** Have all events (experiment_start, round_start/end, experiment_end)
- [x] **Metadata:** meta.json exists with git commit
- [x] **Parser:** Generates rounds.csv, clients.csv, summary.csv
- [x] **Plots:** 3 sanity plots look reasonable
- [x] **Reproducibility:** Same seed → similar accuracy (±0.5%)

---

## 🚨 Common Issues & Fixes

### Issue: ImagePullBackOff
```bash
# Image not loaded
minikube image load zerotrust-flbench:latest

# Verify
minikube image ls | grep zerotrust
```

### Issue: CrashLoopBackOff
```bash
# Check logs
kubectl logs -n fl-experiment <pod-name>

# Common causes:
# - Import error: Missing dependency in requirements.txt
# - Syntax error: Test locally first
# - Wrong command: Check Dockerfile CMD
```

### Issue: Pods Stuck in Pending
```bash
# Check resource limits
kubectl describe pod -n fl-experiment <pod-name>

# Reduce limits in fl-deployment.yaml:
#   limits:
#     memory: "1Gi"  # Instead of 2Gi
#     cpu: "1000m"   # Instead of 2000m
```

### Issue: Accuracy Too Low (<0.80)
```bash
# Validate data splits
python scripts/validate_splits.py --num-clients 5 --data-seed 42

# Check loss function
grep "criterion" src/fl_client.py
# Should be: criterion = nn.CrossEntropyLoss()

# Check model forward()
grep "return" src/fl_client.py | grep -A2 "def forward"
# Should return logits (not log_softmax)
```

### Issue: Parser Fails
```bash
# Check log events match parser
cat results/raw/<RUN_ID>/server_*.log | jq '.event' | sort | uniq

# Update parse_logs.py if events changed
```

### Issue: Duration Outliers in Plot
```bash
# Find outlier rounds
cat results/processed/rounds.csv | \
  awk -F, '{if ($5 > 100) print $0}'  # Rounds > 100 seconds

# Inspect those rounds in logs
grep "round_id.*<N>" results/baseline/*/server_*.log
```

---

## 📊 What You Have After Mốc 0

```
results/
├── baseline/
│   └── SEC0_NET0_50rounds/
│       ├── server_SEC0_NET0_<ts>.log
│       ├── fl-client-*.log (×5)
│       └── meta.json
├── processed/
│   ├── rounds.csv
│   ├── clients.csv
│   └── summary.csv
└── figures/
    └── sanity/
        ├── accuracy_vs_round.png
        ├── duration_vs_round.png
        └── ecdf_duration.png
```

---

## ➡️ Next: Day 2

Once Mốc 0 is solid:
1. **Don't touch** SEC1/SEC2/SEC3 yet
2. **Don't run** matrix yet
3. **Do:** Verify parser works on multiple runs
4. **Do:** Add pandas/matplotlib to requirements if missing

**Tomorrow's goal:** SEC1 (NetworkPolicy) — 10 rounds only.

---

**Status:** ⬜ Not Started | ⏳ In Progress | ✅ Complete

Mark your progress:
- [ ] Step 1: Build image
- [ ] Step 2: Load to minikube
- [ ] Step 3: Test 10 rounds
- [ ] Step 4: Inspect logs
- [ ] Step 5: Validate events
- [ ] Step 6: Run Mốc 0 (50 rounds)
- [ ] Step 7: Archive baseline
- [ ] Step 8: Parse to CSV
- [ ] Step 9: Sanity plots
- [ ] Step 10: Reproducibility test
