# Reproducibility Guide

## Software Versions

- **Git commit:** `2b4ac7c2e1b256589e1c5394a95d841ebe3eba68`
- **Python:** 3.11
- **Flower:** 1.7.0
- **PyTorch:** 2.1.0
- **Kubernetes:** v1.28.0 (minikube)
- **Linkerd:** stable-2.14.x
- **CNI:** Calico (for NetworkPolicy support)

## Hardware/Environment

- **CPU:** 4 cores minimum
- **Memory:** 8GB minimum
- **OS:** Linux (tested on Ubuntu 22.04)

## Reproduction Steps

### 1. Clone Repository
```bash
git clone https://github.com/Huy-VNNIC/ZeroTrust-FLBench.git
cd ZeroTrust-FLBench
git checkout 2b4ac7c2e1b256589e1c5394a95d841ebe3eba68
```

### 2. Build Docker Image
```bash
docker build -t zerotrust-flbench:latest .
```

### 3. Setup Minikube
```bash
minikube start --cpus=4 --memory=8192 --driver=docker
minikube image load zerotrust-flbench:latest
```

### 4. Install Linkerd (for SEC2/SEC3)
```bash
curl -sL https://run.linkerd.io/install | sh
linkerd install --crds | kubectl apply -f -
linkerd install | kubectl apply -f -
kubectl annotate namespace fl-experiment linkerd.io/inject=enabled
```

### 5. Run Core Matrix
```bash
python scripts/run_matrix.py \
  --sec-levels SEC0,SEC1,SEC2,SEC3 \
  --net-profiles NET0,NET2 \
  --iid --noniid \
  --seeds 0,1,2,3,4 \
  --num-rounds 50 \
  --output-dir results/core_matrix
```

Duration: ~27-40 hours (20-30min/run × 80)

### 6. Parse Results
```bash
python scripts/parse_logs.py \
  --log-dir results/core_matrix \
  --output-dir results/processed

python scripts/compute_stats.py \
  --input results/processed/summary.csv \
  --output results/processed/statistics.csv
```

### 7. Generate Figures
```bash
python scripts/plot_publication.py \
  --summary-csv results/processed/summary.csv \
  --rounds-csv results/processed/rounds.csv \
  --output-dir results/figures/publication
```

## Data Availability

- **Raw logs:** `results/core_matrix/` (80 runs)
- **Processed data:** `results/processed/summary.csv`
- **Figures:** `results/figures/publication/`

Archive available at: [ZENODO_DOI]

## Citation

```bibtex
@misc{zerotrust-flbench-2026,
  author = {Nguyen, Nhat Huy},
  title = {ZeroTrust-FLBench: Evaluating Zero-Trust Security for Federated Learning on Kubernetes},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/Huy-VNNIC/ZeroTrust-FLBench}
}
```

## Contact

- **Email:** nguyennhathuy11@dtu.edu.vn
- **Issues:** https://github.com/Huy-VNNIC/ZeroTrust-FLBench/issues
