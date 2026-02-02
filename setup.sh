#!/bin/bash
#
# Quick setup script for ZeroTrust-FLBench
# Sets up entire environment from scratch
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ZeroTrust-FLBench Quick Setup            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}[1/8] Checking prerequisites...${NC}"

command -v docker >/dev/null 2>&1 || { echo -e "${RED}Error: docker not found${NC}"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo -e "${RED}Error: kubectl not found${NC}"; exit 1; }
command -v minikube >/dev/null 2>&1 || { echo -e "${RED}Error: minikube not found${NC}"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}Error: python3 not found${NC}"; exit 1; }

echo -e "${GREEN}✓ All prerequisites found${NC}"
echo ""

# Setup Python environment
echo -e "${YELLOW}[2/8] Setting up Python environment...${NC}"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo ""

# Start minikube
echo -e "${YELLOW}[3/8] Starting minikube with Calico CNI...${NC}"

if minikube status | grep -q "Running"; then
    echo -e "${GREEN}✓ Minikube already running${NC}"
else
    minikube start \
        --cpus=4 \
        --memory=8192 \
        --disk-size=20g \
        --cni=calico \
        --kubernetes-version=v1.28.0
    echo -e "${GREEN}✓ Minikube started${NC}"
fi
echo ""

# Enable addons
echo -e "${YELLOW}[4/8] Enabling Kubernetes addons...${NC}"
minikube addons enable metrics-server
echo -e "${GREEN}✓ Addons enabled${NC}"
echo ""

# Build Docker image
echo -e "${YELLOW}[5/8] Building Docker image...${NC}"

if minikube image ls | grep -q "zerotrust-flbench"; then
    echo -e "${GREEN}✓ Image already exists, skipping build${NC}"
    read -p "Rebuild image? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker build -t zerotrust-flbench:latest .
        minikube image load zerotrust-flbench:latest
        echo -e "${GREEN}✓ Image rebuilt${NC}"
    fi
else
    docker build -t zerotrust-flbench:latest .
    minikube image load zerotrust-flbench:latest
    echo -e "${GREEN}✓ Image built and loaded${NC}"
fi
echo ""

# Create namespace
echo -e "${YELLOW}[6/8] Creating Kubernetes namespace...${NC}"
kubectl create namespace fl-experiment --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✓ Namespace created${NC}"
echo ""

# Deploy baseline
echo -e "${YELLOW}[7/8] Deploying baseline FL workload...${NC}"
kubectl apply -f k8s/00-baseline/fl-deployment.yaml
echo -e "${GREEN}✓ Baseline deployed${NC}"
echo ""

# Wait for pods
echo -e "${YELLOW}[8/8] Waiting for pods to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=fl-server -n fl-experiment --timeout=300s || {
    echo -e "${RED}Warning: Server pod not ready within timeout${NC}"
}
echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""

# Print summary
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Setup Complete - Next Steps              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo "✓ Minikube running"
echo "✓ Python environment: venv/"
echo "✓ Docker image: zerotrust-flbench:latest"
echo "✓ Namespace: fl-experiment"
echo "✓ Baseline deployed"
echo ""
echo -e "${YELLOW}Monitor training:${NC}"
echo "  kubectl logs -n fl-experiment -f deployment/fl-server"
echo ""
echo -e "${YELLOW}Check pods:${NC}"
echo "  kubectl get pods -n fl-experiment"
echo ""
echo -e "${YELLOW}Run experiments:${NC}"
echo "  source venv/bin/activate"
echo "  python scripts/run_matrix.py --tier core"
echo ""
echo -e "${YELLOW}Documentation:${NC}"
echo "  docs/getting_started.md - Detailed setup guide"
echo "  docs/experiment_matrix.md - Experiment design"
echo "  docs/measurement_method.md - How to measure properly"
echo ""
echo -e "${GREEN}Happy experimenting! 🚀${NC}"
