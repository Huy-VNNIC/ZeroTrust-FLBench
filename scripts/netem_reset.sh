#!/bin/bash
#
# Reset network emulation (remove tc qdisc)
#
# Usage: ./netem_reset.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Resetting Network Emulation ===${NC}"

# Detect cluster type
CLUSTER_TYPE="unknown"
if kubectl get nodes -o jsonpath='{.items[0].metadata.name}' | grep -q "minikube"; then
    CLUSTER_TYPE="minikube"
elif kubectl get nodes -o jsonpath='{.items[0].metadata.name}' | grep -q "kind"; then
    CLUSTER_TYPE="kind"
fi

echo "Cluster type: $CLUSTER_TYPE"

reset_node() {
    local NODE=$1
    echo -e "${YELLOW}Resetting node: $NODE${NC}"
    
    # Get interface
    INTERFACE=$(kubectl debug node/$NODE -it --image=alpine -- \
        sh -c "ip route | grep default | awk '{print \$5}' | head -1" 2>/dev/null | tr -d '\r')
    
    if [ -z "$INTERFACE" ]; then
        INTERFACE="eth0"
    fi
    
    echo "  Interface: $INTERFACE"
    echo "  Removing tc qdisc..."
    
    kubectl debug node/$NODE -it --image=nicolaka/netshoot -- \
        tc qdisc del dev $INTERFACE root 2>&1 | grep -v "Defaulted" || echo "  (No qdisc to remove or already clean)"
}

if [ "$CLUSTER_TYPE" == "minikube" ]; then
    echo "Using minikube SSH"
    
    INTERFACE=$(minikube ssh "ip route | grep default | awk '{print \$5}' | head -1")
    echo "Interface: $INTERFACE"
    
    minikube ssh "sudo tc qdisc del dev $INTERFACE root 2>/dev/null || echo 'No qdisc to remove'"
    
    echo -e "${GREEN}Verification:${NC}"
    minikube ssh "sudo tc qdisc show dev $INTERFACE"
    
else
    NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')
    
    for NODE in $NODES; do
        reset_node "$NODE"
    done
fi

echo -e "${GREEN}=== Network reset complete ===${NC}"
