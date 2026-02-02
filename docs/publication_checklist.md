# Publication Readiness Checklist

## Is Your ZeroTrust-FLBench Paper Ready for Q1/SCIE Submission?

Use this checklist to assess whether your work meets the standards for a top-tier journal (DCN, IEEE Transactions, etc.).

---

## ✅ Phase 1: Core Experiment Completion

### Baseline Functionality
- [ ] FL baseline (SEC0, NET0) runs successfully for 50 rounds
- [ ] MNIST accuracy reaches 95%+ consistently
- [ ] Logs contain structured JSON events (round_start, round_end, etc.)
- [ ] No pod crashes or Kubernetes errors
- [ ] Can reproduce results across 5 seeds (variance <5%)

### Measurement Infrastructure
- [ ] Prometheus collects CPU, memory, network metrics
- [ ] Application logs and system metrics are timestamp-aligned
- [ ] Network validation (ping, iperf) confirms emulation profiles
- [ ] Automated collection scripts work reliably
- [ ] Metadata (run_id, config, environment) saved for every run

### Network Emulation
- [ ] NET0, NET2, NET4 profiles apply correctly
- [ ] Validation shows expected delay/jitter/loss
- [ ] Can reset network state reliably between runs
- [ ] Round latency increases proportionally with network impairment

### Security Configurations
- [ ] SEC0 (baseline) works
- [ ] SEC1 (NetworkPolicy) works without breaking DNS or connectivity
- [ ] SEC2 (mTLS) works with Linkerd/Istio installed
- [ ] SEC3 (both) works without conflicts
- [ ] Can deploy and teardown each config reliably

---

## ✅ Phase 2: Experiment Execution

### Core Set (Tier 1)
- [ ] 80 runs completed (MNIST, IID+NonIID, 5 clients, NET0+NET2, SEC0-SEC3, 5 seeds)
- [ ] <10% failure rate across all runs
- [ ] All runs have complete logs and metadata
- [ ] Invalid runs identified and re-run with same seed
- [ ] Results directory organized: `results/raw/<run_id>/`

### Extended Set (Tier 2) — Optional but Recommended
- [ ] Added NET4 (high impairment) runs
- [ ] Added 10-client scale runs
- [ ] Total: 240-320 runs

### Generality Set (Tier 3) — Optional
- [ ] Added CIFAR-10 workload runs
- [ ] Total: 480 runs

---

## ✅ Phase 3: Data Analysis

### Data Processing
- [ ] Parser scripts extract metrics from all runs
- [ ] Summary metrics computed: TTA, p50/p95/p99 latency, bytes/round, failure rate
- [ ] Aggregation across seeds: mean + 95% CI
- [ ] Processed data saved to `results/processed/`

### Statistical Rigor
- [ ] 5 repeats per configuration (minimum)
- [ ] Confidence intervals computed and reported
- [ ] Outliers identified and documented (not silently removed)
- [ ] Hypothesis tests performed where claiming "significant difference" (e.g., Mann-Whitney U)

### Quality Checks
- [ ] All runs have complete data (no truncated logs)
- [ ] Network validation passed for all runs
- [ ] Prometheus metrics cover ≥90% of rounds
- [ ] Data anomalies (e.g., OOM kills) documented

---

## ✅ Phase 4: Figures and Tables

### Required Figures (Minimum 6-8)
- [ ] **Fig 1:** System architecture diagram
- [ ] **Fig 2:** Design-space heatmap (p99 latency or TTA across SEC × NET)
- [ ] **Fig 3:** Round latency distribution (ECDF or boxplot, SEC0-SEC3)
- [ ] **Fig 4:** Time-to-target-accuracy (bar chart with 95% CI)
- [ ] **Fig 5:** Communication overhead (bytes/round)
- [ ] **Fig 6:** Resource overhead (CPU/memory bar chart)
- [ ] **Fig 7:** Failure analysis (bar/stacked chart)
- [ ] **Fig 8:** Guidelines/decision tree (optional but impactful)

### Figure Quality Standards
- [ ] All figures have captions
- [ ] Axes labeled with units
- [ ] Legends clear and readable
- [ ] Font size readable (at least 10pt in final PDF)
- [ ] Colors: colorblind-friendly palette
- [ ] Error bars: 95% CI, not std dev
- [ ] Referenced in text: "as shown in Figure X..."

### Required Tables (Minimum 3-4)
- [ ] **Table 1:** Security configurations (SEC0-SEC3)
- [ ] **Table 2:** Network profiles (NET0-NET5)
- [ ] **Table 3:** Experiment matrix (dimensions, total runs)
- [ ] **Table 4:** Key results summary (p99 latency, TTA, overhead %)

---

## ✅ Phase 5: Paper Writing

### Abstract (150-200 words)
- [ ] Problem statement (1-2 sentences)
- [ ] Approach (2-3 sentences)
- [ ] Key results (2-3 sentences with numbers)
- [ ] Impact/contribution (1-2 sentences)
- [ ] Keywords included (5-7 relevant terms)

### Introduction (1.5-2 pages)
- [ ] Motivation: why FL on K8s + why security matters
- [ ] Problem: gap in understanding security-performance trade-offs
- [ ] Challenges (3-4 key challenges)
- [ ] Contributions (3 concrete bullets)
- [ ] Paper organization

### Research Questions (in Introduction)
- [ ] RQ1: Round latency and failures
- [ ] RQ2: Time-to-accuracy and overhead
- [ ] RQ3: Sweet spots and guidelines
- [ ] (Optional) RQ4: Policy-based adaptation

### Threat Model (0.5-1 page)
- [ ] Adversary capabilities clearly defined
- [ ] Scope clearly stated (what IS and IS NOT covered)
- [ ] Justification for scope
- [ ] Out-of-scope threats acknowledged

### Methodology (2-3 pages)
- [ ] System architecture diagram
- [ ] Security configurations defined
- [ ] Network profiles defined
- [ ] FL metrics defined precisely
- [ ] Measurement methodology explained (timestamps, alignment, repeats)
- [ ] Reproducibility: how others can replicate

### Experimental Setup (1.5-2 pages)
- [ ] Infrastructure details (K8s version, minikube/cluster, resources)
- [ ] Workload specifications (model, dataset, hyperparameters)
- [ ] Data distribution (IID vs Non-IID)
- [ ] Experiment matrix table
- [ ] Automation described

### Results (4-5 pages)
- [ ] One subsection per RQ
- [ ] Every claim backed by figure or table
- [ ] All figures referenced in text
- [ ] Error bars and CI reported
- [ ] Negative results included (if any)

### Discussion (1.5-2 pages)
- [ ] Explanation of key findings (why mTLS increases latency, why NetworkPolicy fails, etc.)
- [ ] Implications for practitioners
- [ ] Generalizability discussed
- [ ] Limitations acknowledged

### Related Work (1-1.5 pages)
- [ ] FL on Kubernetes (3-5 papers)
- [ ] Service mesh performance (3-5 papers)
- [ ] Secure FL (3-5 papers)
- [ ] Network-aware FL (3-5 papers)
- [ ] Gap clearly articulated

### Conclusion (0.5 page)
- [ ] Summarize contributions
- [ ] Restate key findings (with numbers)
- [ ] Future work (2-3 directions)

---

## ✅ Phase 6: Reproducibility and Artifacts

### Code and Configuration
- [ ] All source code in GitHub (or equivalent)
- [ ] README with setup instructions
- [ ] Dockerfile with exact dependency versions
- [ ] Kubernetes manifests for all SEC configs
- [ ] Experiment runner script
- [ ] Data processing scripts
- [ ] Figure generation scripts

### Documentation
- [ ] Getting started guide
- [ ] Threat model document
- [ ] Measurement methodology document
- [ ] Experiment matrix document
- [ ] Troubleshooting guide

### Data Availability
- [ ] Raw logs available (or anonymized subset)
- [ ] Processed results (summary CSV/JSON)
- [ ] Metadata for all runs
- [ ] (Optional) Docker image for easy replication

### Versioning
- [ ] All tools and versions documented (environment.yaml)
- [ ] Git commit hash or release tag for reproducibility
- [ ] License file (e.g., MIT, Apache 2.0)

---

## ✅ Phase 7: Quality Checks

### Technical Correctness
- [ ] No claims without evidence
- [ ] All metrics defined precisely
- [ ] Statistical methods appropriate (non-parametric for latency)
- [ ] No p-hacking (didn't cherry-pick configs or seeds)
- [ ] Honest about failures and limitations

### Writing Quality
- [ ] Grammar and spelling checked (Grammarly, etc.)
- [ ] Consistent terminology throughout
- [ ] No informal language ("cool", "interesting", etc.)
- [ ] Active voice preferred over passive
- [ ] Concise (no unnecessary words)

### Formatting
- [ ] Journal template applied (DCN, IEEE Transactions, etc.)
- [ ] References formatted correctly (author-year or numbered)
- [ ] Equations numbered if referenced
- [ ] Table and figure numbers sequential
- [ ] Page limit respected (typically 10-12 pages for journal)

### References
- [ ] 20-30 references (typical for systems paper)
- [ ] Recent work cited (50%+ from last 3-5 years)
- [ ] Mix of conferences and journals
- [ ] All URLs checked (no dead links)
- [ ] Self-citations reasonable (<20%)

---

## ✅ Phase 8: Pre-Submission Review

### Internal Review
- [ ] Co-authors reviewed and approved
- [ ] Advisor/supervisor reviewed
- [ ] Lab mates or colleagues provided feedback
- [ ] Addressed all comments

### External Feedback (Optional but Valuable)
- [ ] Presented at lab meeting or seminar
- [ ] Posted preprint (arXiv) and got feedback
- [ ] Contacted authors of related work

### Checklist Items
- [ ] Title is specific and descriptive
- [ ] Abstract is self-contained
- [ ] All figures and tables have captions
- [ ] All sections referenced in table of contents
- [ ] No "TODO" or placeholders left
- [ ] Acknowledgments included (funding, resources)
- [ ] Conflict of interest statement (if required)

---

## 🎯 Final Assessment: Are You Ready?

### Minimum Bar for Submission (Must Have ALL)
- [x] Core experiments completed (80+ runs)
- [x] 6-8 figures showing clear trends
- [x] 3+ tables summarizing configs and results
- [x] Statistical rigor (repeats, CI, hypothesis tests)
- [x] Reproducibility (code, configs, docs public)
- [x] Paper follows journal template
- [x] Limitations clearly acknowledged
- [x] Related work comprehensive (20+ citations)

### Strong Submission (Target These for Q1)
- [ ] Extended experiments (320+ runs)
- [ ] Generality across 2+ workloads
- [ ] Deployment guidelines (decision tree or table)
- [ ] Negative results analyzed (why SEC3 fails under loss)
- [ ] Replication by external party (optional but gold standard)
- [ ] Preprint with >3 citations or downloads
- [ ] Clear impact statement (who benefits, how)

### Exceptional Submission (Bonus Points)
- [ ] Full matrix (480 runs)
- [ ] Real edge device validation (not just emulation)
- [ ] Policy-based adaptation (RQ4)
- [ ] Energy consumption analysis
- [ ] Multi-cluster experiments
- [ ] Tool/framework released and adopted

---

## 📊 Scoring Guide

**Count your checkmarks:**

- **0-20:** Early stage, more work needed
- **21-40:** Good progress, focus on experiments
- **41-60:** Experiments done, need analysis and writing
- **61-80:** Near complete, polish and review needed
- **81-100:** Ready for submission! 🎉

---

## 🚀 Common Rejection Reasons to Avoid

1. **Insufficient evaluation:** Only 1-2 configs, no repeats
   - Fix: Run core matrix (80 runs minimum)

2. **No statistical rigor:** Only mean, no CI or variance
   - Fix: Report 95% CI, do hypothesis tests

3. **Unclear contribution:** "We measured X" but so what?
   - Fix: Extract guidelines, show sweet spots

4. **Not reproducible:** No code, vague setup
   - Fix: Public GitHub, detailed docs

5. **Limited scope:** Only datacenter, or only 1 workload
   - Fix: Include edge conditions, IID + Non-IID

6. **Weak related work:** 5-10 papers, all old
   - Fix: 20-30 citations, 50% recent

7. **Overselling:** Claims not backed by data
   - Fix: Every claim has figure/table reference

8. **Ignoring limitations:** "Our work is perfect"
   - Fix: Honest limitations section

---

## 📅 Timeline to Submission

If you have **core experiments done**:

- **Week 1-2:** Data analysis, generate all figures
- **Week 3:** Write Methods, Results sections
- **Week 4:** Write Intro, Related Work, Discussion
- **Week 5:** Polish, internal review
- **Week 6:** Address feedback, final checks
- **Week 7:** Submit! 🚀

Total: **~7 weeks from core experiments to submission**

---

## 🎓 When to Submit

### Green Lights (Go Ahead)
- ✅ Minimum bar checklist 100% complete
- ✅ 2+ co-authors reviewed and approved
- ✅ Results are "boring" (predictable) but rigorous
- ✅ You can defend every claim

### Red Flags (Wait)
- ❌ <50 runs completed
- ❌ Missing figures or analysis
- ❌ Can't explain why results came out that way
- ❌ No code/configs ready for release
- ❌ Advisor says "needs more work"

---

**Use this checklist iteratively throughout your project. Update as you complete items.**

**Last updated:** 2026-02-02
