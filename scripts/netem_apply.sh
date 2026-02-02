#!/bin/bash
#
# Apply network emulation profile to Kubernetes node(s)
# Uses tc (traffic control) with netem (network emulator)
#
# Usage: ./netem_apply.sh <PROFILE>
# Example: ./netem_apply.sh NET2

set -e

PROFILE=$1

if [ -z "$PROFILE" ]; then
    echo "Usage: $0 <PROFILE>"
    echo "Available profiles: NET0, NET1, NET2, NET3, NET4, NET5"
    exit 1
fi

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Applying Network Profile: $PROFILE ===${NC}"

# Define network profiles
declare -A PROFILES

# NET0: No impairment (baseline)
PROFILES[NET0]="none"

# NET1: Low-latency edge (20ms delay, 5ms jitter)
PROFILES[NET1]="delay 20ms 5ms distribution normal"

# NET2: Typical edge/4G (80ms delay, 20ms jitter)
PROFILES[NET2]="delay 80ms 20ms distribution normal"

# NET3: Lossy WiFi (0.5% loss)
PROFILES[NET3]="loss 0.5%"

# NET4: Congested edge (50ms delay, 10ms jitter, 1% loss)
PROFILES[NET4]="delay 50ms 10ms distribution normal loss 1%"

# NET5: Bandwidth-limited (10 Mbps)
PROFILES[NET5]="rate 10mbit"

# Get the profile config
NETEM_CONFIG=${PROFILES[$PROFILE]}

if [ -z "$NETEM_CONFIG" ]; then
    echo -e "${RED}Error: Unknown profile $PROFILE${NC}"
    echo "Available: NET0, NET1, NET2, NET3, NET4, NET5"
    exit 1
fi

# Function to apply tc to a node
apply_tc_to_node() {
    local NODE=$1
    local CONFIG=$2
    
    echo -e "${YELLOW}Applying to node: $NODE${NC}"
    
    if [ "$CONFIG" == "none" ]; then
        echo "  Profile is NET0 (no impairment), skipping tc setup"
        return 0
    fi
    
    # Detect network interface (usually eth0 or ens* in minikube/kind)
    INTERFACE=$(kubectl debug node/$NODE -it --image=alpine -- \
        sh -c "ip route | grep default | awk '{print \$5}' | head -1" 2>/dev/null | tr -d '\r')
    
    if [ -z "$INTERFACE" ]; then
        INTERFACE="eth0"  # Fallback
        echo "  Could not detect interface, using default: $INTERFACE"
    else
        echo "  Detected interface: $INTERFACE"
    fi
    
    # Apply tc netem
    echo "  Applying: tc qdisc add dev $INTERFACE root netem $CONFIG"
    
    kubectl debug node/$NODE -it --image=nicolaka/netshoot -- \
        tc qdisc add dev $INTERFACE root netem $CONFIG 2>&1 | grep -v "Defaulted" || true
    
    # Verify
    echo "  Verifying configuration..."
    kubectl debug node/$NODE -it --image=nicolaka/netshoot -- \
        tc qdisc show dev $INTERFACE 2>&1 | grep -v "Defaulted" | head -5 || true
}

# Get cluster type
CLUSTER_TYPE="unknown"
if kubectl get nodes -o jsonpath='{.items[0].metadata.name}' | grep -q "minikube"; then
    CLUSTER_TYPE="minikube"
elif kubectl get nodes -o jsonpath='{.items[0].metadata.name}' | grep -q "kind"; then
    CLUSTER_TYPE="kind"
fi

echo "Detected cluster type: $CLUSTER_TYPE"

# Get all nodes
NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')

if [ -z "$NODES" ]; then
    echo -e "${RED}Error: No nodes found in cluster${NC}"
    exit 1
fi

# Special handling for minikube (single node, direct SSH access)
if [ "$CLUSTER_TYPE" == "minikube" ]; then
    echo -e "${YELLOW}Using minikube SSH for faster setup${NC}"
    
    if [ "$NETEM_CONFIG" == "none" ]; then
        echo "Profile is NET0 (no impairment), skipping setup"
        exit 0
    fi
    
    # Get primary interface
    INTERFACE=$(minikube ssh "ip route | grep default | awk '{print \$5}' | head -1")
    echo "Interface: $INTERFACE"
    
    # Apply tc directly via minikube ssh
    echo "Applying: tc qdisc add dev $INTERFACE root netem $NETEM_CONFIG"
    minikube ssh "sudo tc qdisc add dev $INTERFACE root netem $NETEM_CONFIG" || {
        echo -e "${YELLOW}Warning: tc qdisc already exists, replacing...${NC}"
        minikube ssh "sudo tc qdisc replace dev $INTERFACE root netem $NETEM_CONFIG"
    }
    
    # Verify
    echo -e "${GREEN}Verifying configuration:${NC}"
    minikube ssh "sudo tc qdisc show dev $INTERFACE"
    
else
    # For kind or generic K8s, use kubectl debug
    for NODE in $NODES; do
        apply_tc_to_node "$NODE" "$NETEM_CONFIG"
    done
fi

echo -e "${GREEN}=== Network profile $PROFILE applied successfully ===${NC}"
echo ""
echo "Validation recommended:"
echo "  kubectl exec -n fl-experiment <pod-name> -- ping -c 10 fl-server"
echo ""
echo "To reset: ./netem_reset.sh"
