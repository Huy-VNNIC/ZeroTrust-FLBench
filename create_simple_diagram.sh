#!/bin/bash

# Create a simple ASCII diagram as PDF replacement
cat > simple_diagram.txt << 'EOF'

       ZeroTrust-FLBench Architecture
       
    +----------------+      +------------------+
    |    Client 1    |----->|                  |
    +----------------+      |    FL Server     |
                            |   (Aggregator)   |
    +----------------+      |                  |
    |    Client 2    |----->|                  |
    +----------------+      +------------------+
                            
    +----------------+      Security Configs:
    |    Client 3    |      • SEC0: Baseline
    +----------------+      • SEC1: NetworkPolicy  
                            • SEC2: mTLS
                            • SEC3: Combined
                            
         Network Profiles: NET0 (0ms), NET2 (50ms)
         
    ┌─────────────────────────────────────────────┐
    │           Kubernetes Cluster                │
    └─────────────────────────────────────────────┘

EOF

echo "Simple diagram created"