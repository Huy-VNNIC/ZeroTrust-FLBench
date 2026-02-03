# Fix cho Run Matrix Script

## Vấn đề

Tất cả experiments fail vì:
1. ❌ Script `run_one.py` check Jobs completion nhưng k8s manifest dùng **Deployment** (không phải Jobs)
2. ❌ FedAvg strategy không set `min_fit_clients` nên chỉ sample 2/5 clients thay vì tất cả

## Giải pháp

### 1. Fixed FL Server Strategy (src/fl_server.py)

```python
# BEFORE
strategy = LoggingFedAvg(
    min_available_clients=args.min_clients,
    fraction_fit=args.fraction_fit,
    fraction_evaluate=args.fraction_evaluate,
)

# AFTER
strategy = LoggingFedAvg(
    min_available_clients=args.min_clients,
    min_fit_clients=args.min_clients,  # ✅ Ensure all clients participate
    fraction_fit=args.fraction_fit,
    fraction_evaluate=args.fraction_evaluate,
)
```

### 2. Created Wait Script (scripts/wait_experiment_completion.sh)

Script mới để wait experiment completion bằng cách monitor server logs cho `experiment_end` event:

```bash
./scripts/wait_experiment_completion.sh fl-experiment <run-id> <timeout>
```

### 3. GitHub Actions Workflow

Created `.github/workflows/ci.yml`:
- ✅ Build Docker image
- ✅ Test FL code locally (96% accuracy)
- ✅ Validate K8s manifests
- ✅ Lint Python code
- ✅ Compile LaTeX paper

## Cách chạy sau khi fix

### Rebuild Docker image:
```bash
docker build -t zerotrust-fl:latest .
```

### Test một experiment:
```bash
python3 scripts/run_one.py --sec-level SEC0 --net-profile NET0 --iid --num-rounds 50
```

### Chạy full matrix (80 experiments):
```bash
python3 scripts/run_matrix.py
```

## Kết quả mong đợi

- All 5 clients sẽ participate mỗi round
- ~95% accuracy sau 50 rounds
- Logs có event `experiment_end` khi hoàn thành
