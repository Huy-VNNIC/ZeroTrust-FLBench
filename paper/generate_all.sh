#!/bin/bash
#
# Master script: Generate all paper assets in one go
#
# Usage: ./paper/generate_all.sh
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

SUMMARY_CSV="${REPO_ROOT}/results/processed/summary.csv"
ROUNDS_CSV="${REPO_ROOT}/results/processed/rounds.csv"
FIGURES_DIR="${REPO_ROOT}/results/figures/publication"
OUTPUT_DIR="${REPO_ROOT}/paper"

echo "================================================"
echo "  ZeroTrust-FLBench: Paper Asset Generator"
echo "================================================"
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if [ ! -f "$SUMMARY_CSV" ]; then
    echo "❌ ERROR: $SUMMARY_CSV not found!"
    echo "   Run: python scripts/parse_logs.py first"
    exit 1
fi

if [ ! -f "$ROUNDS_CSV" ]; then
    echo "❌ ERROR: $ROUNDS_CSV not found!"
    echo "   Run: python scripts/parse_logs.py first"
    exit 1
fi

echo "✅ Data files found"
echo ""

# Step 1: Generate publication figures
echo "================================================"
echo "Step 1/3: Generating publication figures"
echo "================================================"
echo ""

python "${REPO_ROOT}/scripts/plot_publication.py" \
    --summary-csv "$SUMMARY_CSV" \
    --rounds-csv "$ROUNDS_CSV" \
    --output-dir "$FIGURES_DIR"

if [ $? -ne 0 ]; then
    echo "❌ Figure generation failed!"
    exit 1
fi

echo ""
echo "✅ Figures generated in: $FIGURES_DIR"
echo ""

# Step 2: Export paper assets
echo "================================================"
echo "Step 2/3: Exporting paper assets"
echo "================================================"
echo ""

python "${REPO_ROOT}/scripts/export_paper_assets.py" \
    --summary-csv "$SUMMARY_CSV" \
    --rounds-csv "$ROUNDS_CSV" \
    --figures-dir "$FIGURES_DIR" \
    --output-dir "$OUTPUT_DIR"

if [ $? -ne 0 ]; then
    echo "❌ Asset export failed!"
    exit 1
fi

echo ""
echo "✅ Assets exported to: $OUTPUT_DIR"
echo ""

# Step 3: Get git commit for reproducibility
echo "================================================"
echo "Step 3/3: Recording reproducibility info"
echo "================================================"
echo ""

COMMIT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
COMMIT_SHORT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "Git commit: $COMMIT_HASH"

# Update repro.md with actual commit
sed -i "s/\[GIT_COMMIT\]/$COMMIT_SHORT/g" "${OUTPUT_DIR}/repro.md" 2>/dev/null || true

echo ""
echo "================================================"
echo "✅ DONE! Paper assets ready"
echo "================================================"
echo ""
echo "📂 Output structure:"
echo "   ${OUTPUT_DIR}/"
echo "   ├── figures/               # 6 publication figures (PDF + PNG)"
echo "   ├── tables/                # LaTeX table1_summary.tex"
echo "   ├── REPORT.md              # Key findings with numbers"
echo "   ├── repro.md               # Reproducibility guide"
echo "   ├── manuscript.tex         # Paper template"
echo "   └── references.bib         # BibTeX references"
echo ""
echo "📝 Next steps:"
echo "   1. Review REPORT.md for key numbers"
echo "   2. Fill placeholders in manuscript.tex:"
echo "      python paper/fill_placeholders.py"
echo "   3. Compile LaTeX:"
echo "      cd paper && pdflatex manuscript.tex"
echo ""
echo "⏱️  Estimated time to full draft: 8-12 hours"
echo "   (assuming Results section takes 2-4 hours)"
echo ""
echo "================================================"
