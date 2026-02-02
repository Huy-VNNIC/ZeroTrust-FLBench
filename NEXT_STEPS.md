# Next Steps - Roadmap to Publication

**Current Status:** ✅ All critical bugs fixed. Code ready for validation experiments.

---

## Phase 1: Validation (Week 1) - **START HERE**

### Step 1.1: Local Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Verify Flower installation
python -c "import flwr; print(f'Flower version: {flwr.__version__}')"

# Validate data splits
python scripts/validate_splits.py --num-clients 5 --data-seed 42
```

**Expected Output:**
```
✅ PASS: No duplicates, all samples assigned
✅ All validations PASSED
```

### Step 1.2: Docker Build & Test
```bash
# Build image
docker build -t zerotrust-flbench:latest .

# Test image locally (optional)
docker run --rm zerotrust-flbench:latest python /app/src/fl_client.py --help
```

### Step 1.3: Minikube Setup
```bash
# Start minikube with adequate resources
minikube start --cpus=4 --memory=8192 --driver=docker

# Verify Calico CNI (for NetworkPolicy support)
kubectl get pods -n kube-system | grep calico

# Load Docker image into minikube
minikube image load zerotrust-flbench:latest

# Verify image
minikube image ls | grep zerotrust
```

### Step 1.4: Baseline Experiment (SEC0 + NET0)
```bash
# Run first experiment
./scripts/run_one.py \
  --sec-level SEC0 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 10 \
  --iid \
  --data-seed 42 \
  --output-dir results/logs

# Check logs
ls -lh results/logs/

# Inspect server log
jq . results/logs/server_SEC0_NET0_*.log | less

# Verify convergence
jq 'select(.event == "round_complete") | {round: .round, test_acc: .test_accuracy}' \
  results/logs/server_SEC0_NET0_*.log
```

**Expected Results:**
- 10 rounds complete in ~5-10 minutes
- Final test accuracy: 90-95% (MNIST with 5 clients, IID)
- No pod failures or restarts
- RUN_ID present in all log entries

**Troubleshooting:**
- If server pod doesn't start: Check image loaded with `minikube image ls`
- If clients fail: Check server logs for connection errors
- If accuracy low (<80%): Check data split with validation script

### Step 1.5: Reproducibility Test
```bash
# Run same config 3 times
for i in {1..3}; do
  ./scripts/run_one.py \
    --sec-level SEC0 \
    --net-profile NET0 \
    --num-clients 5 \
    --num-rounds 10 \
    --iid \
    --data-seed 42 \
    --output-dir results/logs
  
  # Wait between runs
  sleep 30
done

# Compare final accuracies (should be within 0.5%)
jq -s '[.[] | select(.event == "round_complete" and .round == 10)] | .[].test_accuracy' \
  results/logs/server_SEC0_NET0_*.log
```

**Validation Criteria:**
- ✅ All 3 runs complete successfully
- ✅ Final accuracies differ by <0.5% (e.g., 92.3%, 92.5%, 92.4%)
- ✅ Round durations consistent (CV < 10%)

---

## Phase 2: Security Configurations (Week 2)

### Step 2.1: Create SEC1 (NetworkPolicy) Manifests
```bash
# Copy baseline and modify
cp -r k8s/00-baseline k8s/10-networkpolicy

# Add NetworkPolicy allow-list
cat > k8s/10-networkpolicy/networkpolicies.yaml << 'EOF'
# See docs/security_configs.md for reference
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: fl-experiment
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-fl-traffic
  namespace: fl-experiment
spec:
  podSelector:
    matchLabels:
      app: fl-server
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: fl-client
    ports:
    - protocol: TCP
      port: 8080
EOF

# Update fl-deployment.yaml to add run-id labels (already done in baseline)
```

**Test SEC1:**
```bash
./scripts/run_one.py \
  --sec-level SEC1 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 10
```

**Expected:** Same accuracy as SEC0, <5% latency increase.

### Step 2.2: Install Linkerd (for SEC2/SEC3)
```bash
# Install Linkerd CLI
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh
export PATH=$PATH:$HOME/.linkerd2/bin

# Pre-check
linkerd check --pre

# Install Linkerd into cluster
linkerd install --crds | kubectl apply -f -
linkerd install | kubectl apply -f -

# Verify
linkerd check

# Enable auto-injection for fl-experiment namespace
kubectl annotate namespace fl-experiment linkerd.io/inject=enabled
```

### Step 2.3: Create SEC2 (mTLS only) Manifests
```bash
cp -r k8s/00-baseline k8s/20-mtls

# Add Linkerd injection annotation to namespace
# (Already added via kubectl annotate above)

# Test SEC2
./scripts/run_one.py \
  --sec-level SEC2 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 10
```

**Expected:** ~10-20% latency increase due to mTLS overhead.

### Step 2.4: Create SEC3 (NetworkPolicy + mTLS) Manifests
```bash
cp -r k8s/10-networkpolicy k8s/25-combined

# CRITICAL: Update NetworkPolicy to allow Linkerd proxy port 4143
# Add to allow-fl-traffic NetworkPolicy:
# ingress:
# - from:
#   - podSelector:
#       matchLabels:
#         app: fl-client
#   ports:
#   - protocol: TCP
#     port: 8080
#   - protocol: TCP
#     port: 4143  # Linkerd proxy inbound

# Test SEC3
./scripts/run_one.py \
  --sec-level SEC3 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 10
```

**Expected:** SEC2 + SEC1 overhead combined (~15-25% increase).

---

## Phase 3: Network Profiles & Pilot Experiment (Week 3)

### Step 3.1: Test Network Emulation Script
```bash
# Apply NET1 profile manually to running pod
./scripts/netem_apply.sh fl-experiment fl-client-1 NET1

# Verify tc rules
kubectl exec -n fl-experiment fl-client-1 -- tc qdisc show

# Reset
./scripts/netem_reset.sh fl-experiment fl-client-1
```

### Step 3.2: Run 2×6 Pilot Matrix (12 experiments)
```bash
# Create pilot runner script
cat > scripts/run_pilot.sh << 'EOF'
#!/bin/bash
for SEC in SEC0 SEC1; do
  for NET in NET0 NET1 NET2 NET3 NET4 NET5; do
    echo "Running ${SEC} + ${NET}"
    ./scripts/run_one.py \
      --sec-level $SEC \
      --net-profile $NET \
      --num-clients 5 \
      --num-rounds 10 \
      --iid \
      --data-seed 42 \
      --output-dir results/pilot
    
    # Wait between runs
    sleep 60
  done
done
EOF

chmod +x scripts/run_pilot.sh
./scripts/run_pilot.sh
```

**Duration:** ~4-6 hours (20min/run × 12)

### Step 3.3: Analyze Pilot Results
```bash
# Extract round latencies
python scripts/analyze_logs.py \
  --log-dir results/pilot \
  --output results/pilot_analysis.csv

# Generate preliminary plots
python scripts/plot_results.py \
  --input results/pilot_analysis.csv \
  --output results/plots/
```

**Validation Criteria:**
- ✅ All 12 runs complete successfully
- ✅ TTA increases with network degradation (NET0 < NET5)
- ✅ SEC1/SEC2 add measurable overhead
- ✅ Accuracy remains >85% for all configs

---

## Phase 4: Observability (Week 4)

### Step 4.1: Deploy Prometheus + Grafana
```bash
# Apply manifests
kubectl apply -f k8s/30-observability/

# Port-forward Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Open browser: http://localhost:3000
# Default credentials: admin/admin
```

### Step 4.2: Import FL Dashboard
```bash
# Use dashboard JSON from k8s/30-observability/grafana-dashboard.json
# Import via Grafana UI: Create > Import > Upload JSON
```

### Step 4.3: Validate Metrics Collection
```bash
# Run experiment with Prometheus scraping
./scripts/run_one.py \
  --sec-level SEC0 \
  --net-profile NET0 \
  --num-clients 5 \
  --num-rounds 10

# Query Prometheus for pod CPU
kubectl exec -n monitoring prometheus-0 -- \
  promtool query instant http://localhost:9090 \
  'container_cpu_usage_seconds_total{namespace="fl-experiment"}'
```

---

## Phase 5: Full Experiment (Weeks 5-7)

### Step 5.1: Update run_matrix.py
```python
# Implement proper matrix runner that calls run_one.py
# Features:
# - Progress tracking (X/240 complete)
# - Retry logic (max 3 retries per config)
# - Checkpoint resume (skip completed runs)
# - ETA estimation
```

### Step 5.2: Run Full 4×6×10 Matrix
```bash
# Total: 240 runs (4 SEC × 6 NET × 10 replicas)
# Duration: ~80 hours (20min/run × 240)

python scripts/run_matrix.py \
  --sec-levels SEC0,SEC1,SEC2,SEC3 \
  --net-profiles NET0,NET1,NET2,NET3,NET4,NET5 \
  --replicas 10 \
  --num-clients 5 \
  --num-rounds 10 \
  --output-dir results/full_matrix \
  --checkpoint results/checkpoint.json
```

**Tips:**
- Run overnight/weekend
- Monitor with `watch kubectl get pods -n fl-experiment`
- Check checkpoint file regularly for progress

---

## Phase 6: Analysis & Paper Writing (Weeks 8-10)

### Step 6.1: Data Processing
```bash
# Parse all logs
python scripts/parse_logs.py \
  --log-dir results/full_matrix \
  --output results/metrics.csv

# Calculate statistics
python scripts/compute_stats.py \
  --input results/metrics.csv \
  --output results/statistics.csv
```

### Step 6.2: Generate Figures
```bash
# Use scripts/plot_results.py to generate:
# - Figure 1: TTA heatmap (SEC × NET)
# - Figure 2: Round latency CDFs per SEC level
# - Figure 3: Accuracy vs. Time scatter
# - Figure 4: Resource overhead bar chart
```

### Step 6.3: Write Paper
Use [docs/paper_structure.md](docs/paper_structure.md) as template:

**Sections to write:**
1. **Abstract** (150-200 words): TTA findings, overhead quantification
2. **Introduction**: Motivate FL security evaluation gap
3. **Background**: FL basics, K8s security primitives
4. **Methodology**: Experiment design, threat model, metrics
5. **Results**: Present figures with statistical analysis
6. **Discussion**: Interpret findings, limitations
7. **Related Work**: Compare to prior FL security studies
8. **Conclusion**: Contributions and future work

**Word Count Target:** 6000-8000 words (DCN typical length)

### Step 6.4: Reproducibility Artifacts
```bash
# Package for submission
tar -czf zerotrust-flbench-artifacts.tar.gz \
  src/ k8s/ scripts/ docs/ results/statistics.csv \
  README.md BUGFIX_SUMMARY.md requirements.txt Dockerfile

# Generate CITATION.cff
cat > CITATION.cff << 'EOF'
cff-version: 1.2.0
title: ZeroTrust-FLBench
message: "If you use this software, please cite it as below."
authors:
  - family-names: Nguyen
    given-names: Nhat Huy
    email: nguyennhathuy11@dtu.edu.vn
    affiliation: Duy Tan University
repository-code: https://github.com/Huy-VNNIC/ZeroTrust-FLBench
license: MIT
EOF
```

---

## Phase 7: Submission (Week 11-12)

### Step 7.1: Pre-Submission Checklist
Use [docs/publication_checklist.md](docs/publication_checklist.md):

- [ ] All figures have captions and are referenced in text
- [ ] Statistical tests reported (t-tests, ANOVA, effect sizes)
- [ ] Reproducibility statement included
- [ ] Code and data availability statement
- [ ] Ethics/IRB statement (if needed)
- [ ] Acknowledgments (funding, infrastructure)
- [ ] References formatted per journal style

### Step 7.2: Submit to Digital Communications and Networks (DCN)
- **Journal URL:** https://www.sciencedirect.com/journal/digital-communications-and-networks
- **Impact Factor:** Q1 SCIE (JCR 2022: 7.9)
- **Review Time:** ~3-6 months
- **Open Access:** Optional (APC ~$1500 USD)

**Submission Materials:**
- Main manuscript (PDF)
- Cover letter
- Highlights (3-5 bullet points)
- Graphical abstract (optional)
- Supplementary materials (artifacts tarball)

### Step 7.3: Prepare for Revisions
- Expect 2-3 rounds of revisions
- Common reviewer concerns:
  * Statistical rigor (power analysis, multiple comparison correction)
  * Generalizability (other FL algorithms, datasets)
  * Threat model realism
  * Comparison to related work

---

## Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1. Validation | 1 week | Working baseline experiment |
| 2. Security Configs | 1 week | SEC0-SEC3 manifests validated |
| 3. Network + Pilot | 1 week | 2×6 pilot matrix complete |
| 4. Observability | 1 week | Prometheus/Grafana dashboards |
| 5. Full Experiment | 3 weeks | 4×6×10 matrix (240 runs) |
| 6. Analysis + Writing | 3 weeks | Full draft + figures |
| 7. Submission | 2 weeks | Submitted to DCN |
| **Total** | **12 weeks** | **Paper under review** |

---

## Success Criteria

### Technical Milestones
- ✅ All 4 bugs fixed (DONE)
- [ ] Baseline experiment completes with >90% accuracy
- [ ] SEC1-SEC3 manifests tested and working
- [ ] Full 240-run matrix completes with <5% failure rate
- [ ] All figures generated and publication-ready

### Research Quality
- [ ] Reproducibility: Another researcher can run experiments from README
- [ ] Statistical rigor: Effect sizes reported with confidence intervals
- [ ] Novel insights: Clear findings about SEC/NET trade-offs
- [ ] Practical impact: Recommendations for FL practitioners

### Publication Metrics
- [ ] Paper accepted at Q1 SCIE journal (DCN or equivalent)
- [ ] GitHub repository has >10 stars
- [ ] Code cited in follow-up work within 1 year

---

## Contingency Plans

### If Accuracy Too Low
- Check data split validation
- Increase rounds to 20
- Switch to CIFAR-10 (more complex)
- Verify loss function implementation

### If Experiments Take Too Long
- Reduce replicas from 10 to 5
- Use fewer clients (3 instead of 5)
- Focus on SEC0-SEC1 only (defer SEC2-SEC3)
- Prioritize 2×6 pilot for initial submission

### If Paper Rejected
- Submit to backup venues:
  * IEEE Transactions on Network and Service Management (TNSM)
  * IEEE Access (open access, faster review)
  * ICML/NeurIPS workshops (FL-related)
- Incorporate reviewer feedback
- Add more experiments if requested

---

## Resources & References

### Documentation
- [BUGFIX_SUMMARY.md](BUGFIX_SUMMARY.md) - All bug fixes explained
- [docs/threat_model.md](docs/threat_model.md) - Security scope
- [docs/measurement_method.md](docs/measurement_method.md) - FL metrics
- [docs/experiment_matrix.md](docs/experiment_matrix.md) - Full design

### External References
- **Flower Docs:** https://flower.ai/docs/
- **Linkerd Docs:** https://linkerd.io/2.14/overview/
- **K8s NetworkPolicy:** https://kubernetes.io/docs/concepts/services-networking/network-policies/
- **DCN Journal:** https://www.sciencedirect.com/journal/digital-communications-and-networks

### Similar Works (for Related Work section)
1. "Federated Learning Over Wireless Networks" (IEEE CommMag 2021)
2. "Security and Privacy in Federated Learning" (IEEE Access 2020)
3. "Network-Aware Federated Learning" (MobiCom 2022)

---

## Getting Help

### Common Issues
1. **Minikube won't start:** Try `minikube delete` then `minikube start`
2. **Image not found:** Verify with `minikube image ls`
3. **Pods CrashLoopBackOff:** Check logs with `kubectl logs -n fl-experiment <pod>`
4. **NetworkPolicy blocks traffic:** Temporarily remove with `kubectl delete networkpolicy -n fl-experiment --all`

### Contact
- **GitHub Issues:** https://github.com/Huy-VNNIC/ZeroTrust-FLBench/issues
- **Email:** nguyennhathuy11@dtu.edu.vn

---

**Good luck! 🚀 Hãy "đào sâu" và tránh "đề tài rác"! 📊**
