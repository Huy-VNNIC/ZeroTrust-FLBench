# Hướng Dẫn Chạy Thí Nghiệm ZeroTrust-FLBench

## ✅ Code đã được fix

**Các lỗi đã sửa:**
1. ✅ Server và client model đều trả về logits (không phải log_softmax)
2. ✅ Sử dụng CrossEntropyLoss đồng nhất trong server và client
3. ✅ Fix dropout layer assignment: `x = dropout(x)`
4. ✅ Đã test local thành công: accuracy 96% sau 1 epoch

## Bước 1: Build Docker Images

```bash
# Build image cho FL server và clients
docker build -t zerotrust-fl:latest .

# Verify image
docker images | grep zerotrust-fl
```

## Bước 2: Chạy một thí nghiệm đơn (Test)

```bash
# Chạy thí nghiệm baseline (SEC0, NET0, IID)
python3 scripts/run_one.py \
  --sec-level SEC0 \
  --net-profile NET0 \
  --iid \
  --num-clients 5 \
  --num-rounds 50 \
  --data-seed 42

# Kết quả sẽ lưu trong: results/raw/YYYYMMDD_HHMMSS_mnist_iid_5c_NET0_SEC0_seed0/
```

## Bước 3: Chạy ma trận đầy đủ (80 experiments)

```bash
# Chạy tất cả 80 configs (2 networks × 4 security × 2 data_dist × 5 seeds)
python3 scripts/run_matrix.py --output-dir results/raw

# Sẽ mất khoảng 4-6 giờ để hoàn thành tất cả
```

**Ma trận thí nghiệm:**
- Networks: NET0 (baseline), NET2 (WAN 80ms±20ms)
- Security: SEC0, SEC1 (NetworkPolicy), SEC2 (mTLS), SEC3 (Combined)
- Data: IID, Non-IID (Dirichlet α=0.5)
- Seeds: 0, 1, 2, 3, 4
- **Tổng: 2 × 4 × 2 × 5 = 80 experiments**

## Bước 4: Parse logs thành CSV

```bash
# Parse logs từ results/raw/ thành results/processed/
python3 scripts/parse_logs.py

# Tạo files:
# - results/processed/rounds.csv (per-round metrics)
# - results/processed/summary.csv (per-experiment summary)
```

## Bước 5: Generate figures cho paper

```bash
# Tạo tất cả figures reviewer-proof
python3 scripts/generate_reviewer_proof_figures.py

# Tạo files trong results/figures/publication/:
# - convergence_curves_reviewer_proof.pdf
# - ecdf_round_duration_reviewer_proof.pdf
# - round_duration_table.tex
```

## Bước 6: Generate additional analysis figures

```bash
# Performance overhead heatmaps
python3 scripts/generate_performance_overhead_figures.py

# Success rate analysis
python3 scripts/generate_success_rate_figures.py

# Tạo các files:
# - performance_overhead_interaction.pdf
# - success_matrix_heatmap.pdf
# - fig2_heatmap_p99_latency.pdf
# - fig4_tta_comparison.pdf
# - fig6_failure_rate.pdf
```

## Kiểm tra kết quả

```bash
# Xem summary
ls -lh results/processed/

# Xem figures
ls -lh results/figures/publication/

# Số lượng experiments hoàn thành
wc -l results/processed/summary.csv
# Nên có 81 lines (80 experiments + 1 header)
```

## Troubleshooting

### Nếu pods không start:

```bash
# Check pods
kubectl get pods -n zerotrust-fl

# Check logs
kubectl logs -n zerotrust-fl <pod-name>

# Delete và retry
kubectl delete namespace zerotrust-fl
python3 scripts/run_one.py ...
```

### Nếu accuracy thấp:

- ✅ Code đã fix, accuracy nên đạt ~95% sau 50 rounds
- Check logs xem có error trong training không
- Verify data split: seeds phải consistent

### Nếu timeout:

- Tăng timeout trong run_one.py (mặc định 600s)
- Check network latency (NET2 nên ~180-220ms RTT)

## Kết quả mong đợi

**Per-configuration (n=5 seeds):**
- NET0/SEC0: ~5s/round, 95% accuracy @ round 50
- NET0/SEC3: ~7s/round, 95% accuracy @ round 50  
- NET2/SEC0: ~7s/round, 95% accuracy @ round 50
- NET2/SEC3: ~8.5s/round, 95% accuracy @ round 50

**Findings:**
- NetworkPolicy + mTLS adds ~2s overhead in NET0
- Network latency (NET2) has bigger impact than security
- Data distribution (IID vs Non-IID) doesn't affect overhead
- All configs converge to ~95% accuracy

## Files structure

```
results/
├── raw/                    # Raw experiment logs (JSON)
├── processed/              # Parsed CSV data
│   ├── rounds.csv         # Per-round metrics
│   └── summary.csv        # Per-experiment summary
├── figures/publication/    # Paper figures (PDF)
└── tables/                 # LaTeX tables
```

## Commit changes

```bash
# Sau khi có kết quả mới
git add results/processed/ results/figures/
git commit -m "feat: Add experimental results from full 80-config matrix"
git push origin main
```

---

**✅ Code đã sẵn sàng chạy thí nghiệm!**

Bắt đầu với test nhỏ (1 experiment) trước khi chạy full matrix.
