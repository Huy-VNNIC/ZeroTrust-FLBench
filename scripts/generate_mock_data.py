#!/usr/bin/env python3
"""
Generate mock data to test plot_publication.py

Creates synthetic summary.csv and rounds.csv matching expected schema
"""

import pandas as pd
import numpy as np
from pathlib import Path

np.random.seed(42)

# Create mock summary data
records = []
for sec in ['SEC0', 'SEC1', 'SEC2', 'SEC3']:
    for net in ['NET0', 'NET2']:
        for iid in [True, False]:
            for seed in range(5):
                run_id = f"{sec}_{net}_{'IID' if iid else 'NonIID'}_seed{seed}"
                
                # Simulate latency (SEC3 > SEC2 > SEC1 > SEC0)
                base_latency = 5.0
                sec_overhead = {'SEC0': 0, 'SEC1': 0.15, 'SEC2': 0.25, 'SEC3': 0.35}[sec]
                net_overhead = {'NET0': 0, 'NET2': 1.5}[net]
                
                p50 = base_latency * (1 + sec_overhead) + net_overhead + np.random.normal(0, 0.3)
                p95 = p50 * 1.3 + np.random.normal(0, 0.5)
                p99 = p50 * 1.5 + np.random.normal(0, 0.7)
                
                # TTA: higher for SEC3 and NET2
                base_tta = 200
                tta = base_tta * (1 + sec_overhead) * (1 + net_overhead/10) + np.random.normal(0, 20)
                
                # Failure rate: higher for SEC3/NET2
                base_failure = 0.01
                if sec == 'SEC3' and net == 'NET2':
                    failure_rate = base_failure * 5 + np.random.uniform(0, 0.02)
                elif sec == 'SEC3':
                    failure_rate = base_failure * 3 + np.random.uniform(0, 0.01)
                else:
                    failure_rate = base_failure + np.random.uniform(0, 0.005)
                
                records.append({
                    'run_id': run_id,
                    'sec_level': sec,
                    'net_profile': net,
                    'iid': iid,
                    'seed': seed,
                    'p50_round': max(p50, 0.1),
                    'p95_round': max(p95, 0.1),
                    'p99_round': max(p99, 0.1),
                    'tta_95': max(tta, 50) if np.random.random() > 0.1 else np.nan,  # 10% missing
                    'tta_97': max(tta * 1.1, 50) if np.random.random() > 0.1 else np.nan,
                    'failure_rate': min(failure_rate, 0.1),
                    'completed_rounds': 50 if failure_rate < 0.05 else 48,
                    'total_rounds': 50,
                })

summary_df = pd.DataFrame(records)

# Create mock rounds data
rounds_records = []
for _, row in summary_df.iterrows():
    run_id = row['run_id']
    base_duration = row['p50_round']
    
    for round_id in range(1, 51):
        # Simulate round duration (slightly increasing with round)
        duration = base_duration * (1 + 0.002 * round_id) + np.random.normal(0, 0.5)
        
        # Simulate accuracy convergence (logistic curve)
        max_acc = 0.95 + np.random.normal(0, 0.02)
        accuracy = max_acc / (1 + np.exp(-0.15 * (round_id - 25))) + np.random.normal(0, 0.01)
        accuracy = np.clip(accuracy, 0.1, 1.0)
        
        rounds_records.append({
            'run_id': run_id,
            'round_id': round_id,
            'duration': max(duration, 0.1),
            'accuracy': accuracy,
            'loss': 2.3 * np.exp(-0.1 * round_id) + np.random.normal(0, 0.05),
        })

rounds_df = pd.DataFrame(rounds_records)

# Save to results/processed/
output_dir = Path("results/processed")
output_dir.mkdir(parents=True, exist_ok=True)

summary_df.to_csv(output_dir / "summary.csv", index=False)
rounds_df.to_csv(output_dir / "rounds.csv", index=False)

print(f"✅ Generated mock data:")
print(f"   {output_dir}/summary.csv ({len(summary_df)} runs)")
print(f"   {output_dir}/rounds.csv ({len(rounds_df)} rounds)")
print("")
print("📊 Summary stats:")
print(f"   SEC levels: {summary_df['sec_level'].unique()}")
print(f"   NET profiles: {summary_df['net_profile'].unique()}")
print(f"   IID splits: {summary_df['iid'].unique()}")
print(f"   Seeds: {summary_df['seed'].unique()}")
print("")
print("🎨 Now run:")
print("   python scripts/plot_publication.py \\")
print("     --summary-csv results/processed/summary.csv \\")
print("     --rounds-csv results/processed/rounds.csv \\")
print("     --output-dir results/figures/publication")
