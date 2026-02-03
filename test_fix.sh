#!/bin/bash
# Quick test script to verify fix works

set -e

echo "🧪 Testing ZeroTrust-FLBench fix..."
echo ""

# Cleanup any existing namespace
echo "🧹 Cleaning up old experiments..."
kubectl delete namespace fl-experiment --ignore-not-found=true --wait=true 2>/dev/null || true
sleep 2

echo "✅ Clean slate ready"
echo ""

# Run ONE short experiment (5 rounds)
echo "🚀 Running test experiment (SEC0, NET0, IID, 5 rounds)..."
echo "   This should take ~2-3 minutes..."
echo ""

timeout 300 python3 scripts/run_one.py \
  --sec-level SEC0 \
  --net-profile NET0 \
  --iid \
  --num-rounds 5 \
  --output-dir results/raw 2>&1 | tee /tmp/test_run.log

echo ""
echo "📊 Checking results..."

# Check if experiment completed
if grep -q '"event": "experiment_end"' /tmp/test_run.log; then
    echo "✅ Experiment completed successfully!"
    
    # Check logs collected
    LATEST_DIR=$(ls -dt results/raw/202* 2>/dev/null | head -1)
    if [ -d "$LATEST_DIR" ]; then
        echo "✅ Logs collected in: $LATEST_DIR"
        ls -lh "$LATEST_DIR/"
    fi
    
    echo ""
    echo "🎉 TEST PASSED! Fix is working correctly."
    echo ""
    echo "Next steps:"
    echo "1. Run full matrix: python3 scripts/run_matrix.py"
    echo "2. Monitor progress: watch -n 10 'ls -lt results/raw/ | head -10'"
    exit 0
else
    echo "❌ Experiment did not complete properly"
    echo ""
    echo "Debug info:"
    tail -50 /tmp/test_run.log
    exit 1
fi
