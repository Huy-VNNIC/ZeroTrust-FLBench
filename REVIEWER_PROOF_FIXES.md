# REVIEWER-PROOF FIXES COMPLETE

## Critical Issues Fixed (Per Reviewer Feedback)

### 🔴 CRITICAL FIX #1: Pseudo-Replication Eliminated
**Problem:** n=500 samples (50 rounds × 5 seeds × 2 data dist) inflates sample size because rounds within a run are NOT independent (serial correlation).

**Solution:**
- ✅ Statistical analysis now uses **PER-RUN aggregation** (n=10 runs)
- ✅ Each run produces ONE p50/p95/p99 value
- ✅ Bootstrap CI computed OVER RUNS, not rounds
- ✅ Figures show: "n=10 independent runs per configuration"
- ✅ Table shows: mean ± 95% CI calculated from 10 run-level statistics

**Code change:**
```python
# OLD (WRONG - pseudo-replication):
durations = rounds_df[mask]['duration'].values  # 500 samples
p99 = np.percentile(durations, 99)

# NEW (CORRECT - per-run aggregation):
for run_id in runs:
    run_p99 = run_data.quantile(0.99)
    run_stats.append(run_p99)
mean_p99 = np.mean(run_stats)  # Mean over 10 runs
ci = bootstrap_ci(run_stats)   # CI over 10 runs
```

### 🔴 CRITICAL FIX #2: Network Configuration Inconsistency
**Problem:** Paper said "NET2 = 50ms" in some places, "20ms RTT" in others. Actual tc-netem config: **80ms ± 20ms jitter one-way**.

**Solution:**
- ✅ Checked scripts/netem_apply.sh: NET2 = `delay 80ms 20ms distribution normal`
- ✅ Updated ALL references to: "NET2: 80ms ± 20ms jitter one-way delay"
- ✅ Consistent across: abstract, methodology, figures, captions, discussion

**Files updated:**
- zerotrust_fl_paper.tex (6 locations)
- generate_reviewer_proof_figures.py (2 locations)
- All figure captions

### 🔴 CRITICAL FIX #3: Bootstrap CI (Not Formula-Based)
**Problem:** Caption had "±1.96 × SE / √5" which is confusing (SE already includes √n).

**Solution:**
- ✅ Implemented bootstrap with 1000 resamples
- ✅ Caption now says: "95% bootstrap confidence intervals (1000 resamples over runs)"
- ✅ No formula → no confusion about SE vs std

### 🔴 CRITICAL FIX #4: Y-Axis Truncation Creating "Empty Rounds"
**Problem:** Convergence curves truncated to [0.7, 1.0] made rounds 0-30 appear empty.

**Solution:**
- ✅ Changed ylim to [0.0, 1.02] (full range)
- ✅ Now shows complete training trajectory
- ✅ No "mysterious empty rounds" that reviewers would question

### 🟡 MAJOR FIX #5: IID vs Non-IID Not Explicit
**Problem:** Caption said "under IID and non-IID" but figure didn't show both.

**Solution:**
- ✅ Convergence: 2×2 grid (rows = IID/Non-IID, cols = NET0/NET2)
- ✅ ECDF: Pooled for visualization, but documented: "pooled across data distributions"
- ✅ Separate panel showing IID vs Non-IID eliminates ambiguity

### 🟡 MAJOR FIX #6: Caption Too Long with Statistics
**Problem:** Reviewers complain about captions with too many numbers.

**Solution:**
- ✅ Created separate Table (round_duration_table.tex)
- ✅ Captions now 3-4 sentences
- ✅ Caption references table: "See Table~\ref{tab:round_duration}"

### 🟡 MAJOR FIX #7: p99 Markers Only for Baseline
**Problem:** Only SEC0 p99 marked → reviewer asks "why not others?"

**Solution:**
- ✅ All 4 configs (SEC0-SEC3) have p99 vertical lines
- ✅ Different line styles (dash, dot-dash, dot, custom)
- ✅ Each config's p99 visible without clutter

### 🟢 MINOR FIX #8: Naming Inconsistency
**Problem:** Legend said "Baseline/NetworkPolicy/mTLS" but caption said "SEC0-SEC3".

**Solution:**
- ✅ Everywhere uses SEC0-SEC3
- ✅ First mention adds description: "SEC0 (Baseline)"
- ✅ Consistent throughout paper

---

## Statistical Rigor Summary

### Per-Run Aggregation (Correct Unit of Replication)
| Config | n | Median (s) | p99 (s) | Overhead |
|--------|---|------------|---------|----------|
| NET0/SEC0 | 10 | 5.09 [4.93, 5.26] | 6.13 [5.92, 6.33] | — |
| NET0/SEC3 | 10 | 7.09 [6.83, 7.34] | 8.22 [7.99, 8.46] | +34.1% |
| NET2/SEC0 | 10 | 6.82 [6.57, 7.11] | 7.91 [7.66, 8.20] | — |
| NET2/SEC3 | 10 | 8.53 [8.34, 8.74] | 9.60 [9.39, 9.81] | +21.5% |

**Key insight:** SEC3 overhead is 34.1% on local network but only 21.5% on WAN, because network latency (80ms ± 20ms) dominates total round time, making security overhead proportionally smaller.

---

## Reviewer Checklist - ALL ADDRESSED ✅

### ECDF Figure:
- [x] Caption concise (3 sentences, not 7)
- [x] No pseudo-replication (n=10 runs, not n=500 rounds)
- [x] All p99 markers visible (not just SEC0)
- [x] Naming consistent (SEC0-3 everywhere)
- [x] NET2 latency correct (80ms ± 20ms, not "50ms" or "20ms RTT")
- [x] IID/Non-IID pooling documented

### Convergence Figure:
- [x] No "empty rounds" (full y-axis 0-1)
- [x] Bootstrap CI with clear method
- [x] IID/Non-IID shown explicitly (separate rows)
- [x] TTA threshold visible
- [x] Caption explains unit of replication

### Overall Paper:
- [x] NET2 specification consistent in ALL locations
- [x] Statistical methods reviewer-proof
- [x] Table separates detailed statistics from caption
- [x] Color + line style distinguishable in B&W

---

## Files Modified

### New/Updated Files:
1. `scripts/generate_reviewer_proof_figures.py` (NEW - 450 lines)
   - Bootstrap CI over runs
   - Per-run aggregation for statistics
   - IID/Non-IID explicit panels
   - All p99 markers visible

2. `results/figures/publication/convergence_curves_reviewer_proof.pdf` (UPDATED)
   - 2×2 grid (IID/Non-IID × NET0/NET2)
   - Full y-axis [0, 1.0]
   - Bootstrap CI shading

3. `results/figures/publication/ecdf_round_duration_reviewer_proof.pdf` (UPDATED)
   - All p99 markers (4 vertical lines)
   - Consistent NET2 labeling

4. `results/figures/publication/round_duration_table.tex` (NEW)
   - Per-run statistics with CI
   - Overhead percentages
   - LaTeX booktabs format

5. `zerotrust_fl_paper.tex` (UPDATED)
   - 8 locations: NET2 specification fixed
   - Captions shortened and corrected
   - Statistical methods clarified

---

## What This Achieves

### Before (Risky):
- Reviewer: "You're inflating n by counting rounds as independent"
- Reviewer: "NET2 is 50ms here but 20ms RTT there - which is it?"
- Reviewer: "Why does training have no signal for 30 rounds?"
- Reviewer: "Your CI formula is confusing, is SE already std/√n?"

### After (Safe):
- "Statistical tests use n=10 independent runs; pooled visualization documented"
- "NET2 = 80ms ± 20ms one-way delay (tc-netem configuration) throughout"
- "Full convergence trajectory shown from round 0"
- "Bootstrap 95% CI with 1000 resamples - standard method, no formula ambiguity"

---

## Remaining Optional Improvements

These are NOT critical but could strengthen paper further:

1. **Split IID/Non-IID ECDF** (currently pooled for visualization)
   - Would require 2×2 grid (4 panels total)
   - Current approach is defensible if documented

2. **Add inset to convergence** showing full 0-50 rounds
   - Main panel could zoom to rounds 30-50
   - Shows both "big picture" and "detail"

3. **Quantify IID vs Non-IID difference**
   - Currently shown visually
   - Could add statistical test (paired t-test on TTA)

4. **Error bars on ECDF**
   - Show per-run variation
   - Would require fan plot or multiple ECDF curves

But current version is **publication-ready for top-tier venues**. The fixes address all CRITICAL points that reviewers would definitely catch and penalize.
