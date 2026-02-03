#!/bin/bash
# Wait for FL experiment to complete by monitoring server logs

NAMESPACE=${1:-fl-experiment}
RUN_ID=$2
TIMEOUT=${3:-3600}

if [ -z "$RUN_ID" ]; then
    echo "Usage: $0 <namespace> <run-id> [timeout]"
    exit 1
fi

echo "Waiting for experiment completion (run-id=$RUN_ID, timeout=${TIMEOUT}s)..."

START_TIME=$(date +%s)

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    if [ $ELAPSED -gt $TIMEOUT ]; then
        echo "❌ Timeout after ${TIMEOUT}s"
        exit 1
    fi
    
    # Get server pod name
    SERVER_POD=$(kubectl get pods -n $NAMESPACE -l "run-id=$RUN_ID,app=fl-server" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -z "$SERVER_POD" ]; then
        echo "⏳ Waiting for server pod... (${ELAPSED}s)"
        sleep 5
        continue
    fi
    
    # Check if server logs contain experiment_end event
    if kubectl logs -n $NAMESPACE $SERVER_POD 2>/dev/null | grep -q '"event": "experiment_end"'; then
        echo "✅ Experiment completed successfully!"
        exit 0
    fi
    
    # Check if pod failed
    POD_STATUS=$(kubectl get pod -n $NAMESPACE $SERVER_POD -o jsonpath='{.status.phase}' 2>/dev/null)
    if [ "$POD_STATUS" == "Failed" ] || [ "$POD_STATUS" == "Error" ]; then
        echo "❌ Server pod failed (status=$POD_STATUS)"
        exit 1
    fi
    
    echo "⏳ Experiment running... (${ELAPSED}s, status=$POD_STATUS)"
    sleep 10
done
