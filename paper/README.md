# Paper Preparation Guide

## Overview

This directory contains tools for **"chạy xong thí nghiệm là viết paper ngay trong ngày"** workflow.

## Prerequisites

✅ **Before writing paper, you MUST have:**

1. All experiments completed (`results/core_matrix/` with 80 runs)
2. Logs parsed (`results/processed/summary.csv`, `rounds.csv`, `clients.csv`)
3. Statistics computed (`results/processed/statistics.csv`)

## Quick Start: Generate All Paper Assets

**Single command after experiments finish:**

```bash
./paper/generate_all.sh
```

This script:
1. Generates 6 publication figures (PDF + PNG)
2. Creates LaTeX tables
3. Generates REPORT.md with key findings
4. Creates repro.md with reproduction instructions
5. Copies everything to `paper/` directory

## Step-by-Step (Manual)

### Step 1: Generate Publication Figures

```bash
python scripts/plot_publication.py \
  --summary-csv results/processed/summary.csv \
  --rounds-csv results/processed/rounds.csv \
  --output-dir results/figures/publication
```

**Output:** 6 figures in `results/figures/publication/`:
- `fig1_system_overview.pdf/png` – System architecture
- `fig2_heatmap_p99_latency.pdf/png` – Latency heatmap
- `fig3_ecdf_latency.pdf/png` – ECDF distributions
- `fig4_tta_comparison.pdf/png` – TTA bar chart
- `fig5_accuracy_convergence.pdf/png` – Accuracy curves
- `fig6_failure_rate.pdf/png` – Failure rate bars

### Step 2: Export Paper Assets

```bash
python scripts/export_paper_assets.py \
  --summary-csv results/processed/summary.csv \
  --rounds-csv results/processed/rounds.csv \
  --figures-dir results/figures/publication \
  --output-dir paper
```

**Output:** 
- `paper/figures/` – All figures copied
- `paper/tables/table1_summary.tex` – LaTeX summary table
- `paper/REPORT.md` – Key findings with numbers
- `paper/repro.md` – Reproducibility guide

### Step 3: Fill Paper Placeholders

Open `manuscript.tex` and replace placeholders:

```latex
% Find and replace these after experiments:
\P99SEC3NET0       → actual p99 latency (e.g., 12.3)
\P99SEC3NET2       → actual p99 latency under NET2
\TTASEC0NET0       → baseline TTA
\TTASEC3NET2       → SEC3 TTA under NET2
\FAILSEC3NET2      → failure rate percentage
\OVERHEADSEC3      → overhead percentage
\COMMITHASH        → git commit hash
```

**Automated replacement script provided** (see Step 4).

### Step 4: Auto-Fill Numbers

```bash
python paper/fill_placeholders.py \
  --template paper/manuscript.tex \
  --report paper/REPORT.md \
  --output paper/manuscript_filled.tex
```

This extracts numbers from REPORT.md and fills `manuscript.tex` placeholders automatically.

### Step 5: Compile LaTeX

```bash
cd paper
pdflatex manuscript_filled.tex
bibtex manuscript_filled
pdflatex manuscript_filled.tex
pdflatex manuscript_filled.tex
```

**Output:** `manuscript_filled.pdf`

## Files Structure

```
paper/
├── manuscript.tex           # LaTeX paper template (with placeholders)
├── references.bib           # BibTeX references
├── generate_all.sh          # Master script
├── fill_placeholders.py     # Auto-fill numbers
├── README.md                # This file
├── figures/                 # Exported figures (after Step 2)
│   ├── fig1_system_overview.pdf
│   ├── fig2_heatmap_p99_latency.pdf
│   └── ...
├── tables/                  # LaTeX tables (after Step 2)
│   └── table1_summary.tex
├── REPORT.md                # Key findings (after Step 2)
└── repro.md                 # Reproducibility (after Step 2)
```

## Timeline: "Viết Paper Trong Ngày"

| Time       | Task                          | Output                          |
|------------|-------------------------------|---------------------------------|
| 30 min     | Data sanity check             | Validated summary.csv           |
| 1-2 hours  | Generate figures + tables     | 6 figures, 1 table              |
| 2-4 hours  | Write Results + Discussion    | manuscript.tex (RQ1-RQ3)        |
| 1-2 hours  | Fill Abstract + Contributions | manuscript.tex (numbers filled) |
| 1-2 hours  | Related work                  | manuscript.tex (complete)       |
| 1 hour     | Compile + proofread           | manuscript.pdf (draft v1)       |
| **8-12h**  | **TOTAL**                     | **Full draft ready**            |

## Tips for Q1/SCIE Quality

### Figures
- ✅ Vector PDFs (not rasterized)
- ✅ Font size 10-12pt (readable when shrunk)
- ✅ Consistent color scheme (colorblind-friendly)
- ✅ Caption must "stand alone" (reader understands without main text)

### Tables
- ✅ Use `booktabs` package (\toprule, \midrule, \bottomrule)
- ✅ Bold critical numbers
- ✅ Units in column headers
- ✅ Round to 2-3 significant figures

### Writing
- ✅ Each claim must reference a figure/table
- ✅ Results section: facts only (no interpretation)
- ✅ Discussion section: interpretation + guidelines
- ✅ Limitations section: transparent about scope

### Citations
- ✅ Minimum 30 references for Q1
- ✅ Include recent works (2020-2025)
- ✅ Cite competitors' FL frameworks
- ✅ Cite Kubernetes/service mesh benchmarks

## Common Pitfalls (Avoid "Đề Tài Rác")

❌ **Jumping to paper before pipeline is locked**
   → Fix: Follow DAY1_QUICK_START.md first

❌ **Manual copy-paste of numbers**
   → Fix: Use `fill_placeholders.py` auto-fill

❌ **Figures without captions**
   → Fix: Every figure must have standalone caption

❌ **No reproducibility section**
   → Fix: `repro.md` → Appendix A in paper

❌ **Weak Related Work**
   → Fix: 4 categories (FL frameworks, K8s security, service mesh, secure FL)

## Validation Checklist

Before submission, verify:

- [ ] All placeholders filled (no `[XXX]` left)
- [ ] All 6 figures referenced in text
- [ ] Table 1 matches summary.csv data
- [ ] Abstract has 3+ concrete numbers
- [ ] REPORT.md findings appear in Results
- [ ] repro.md → Appendix or supplementary material
- [ ] BibTeX compiles without errors
- [ ] PDF renders correctly (no missing fonts)
- [ ] Commit hash in paper matches GitHub release

## Target Journal: Digital Communications and Networks (DCN)

**Format:** Elsevier elsarticle 3p template (already used in `manuscript.tex`)

**Page Limit:** Typically 10-15 pages

**Sections Required:**
- Abstract (250 words max)
- Keywords (6-8 terms)
- Highlights (3-5 bullet points)
- Main text (Intro, Background, Method, Results, Discussion, Related, Conclusion)
- References (30+ for Q1)

**Submission:** Editorial Manager (online portal)

## Contact

Questions? Check:
1. `DAY_BY_DAY_CHECKLIST.md` (Day 7 section)
2. `REPORT.md` (generated after experiments)
3. GitHub Issues: https://github.com/Huy-VNNIC/ZeroTrust-FLBench/issues
