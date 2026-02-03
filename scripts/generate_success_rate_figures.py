#!/usr/bin/env python3
"""
Generate SUCCESS RATE figures (not just counts) for paper
Fixes the confusing "count" vs "rate" issue
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from scipy import stats

# IEEE style settings
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'DejaVu Sans'],
    'font.size': 9,
    'axes.labelsize': 9,
    'axes.titlesize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'figure.titlesize': 10,
})

def wilson_ci(success, total, alpha=0.05):
    """Wilson score confidence interval for binomial proportion"""
    if total == 0:
        return 0, 0, 0
    p = success / total
    z = stats.norm.ppf(1 - alpha/2)
    denominator = 1 + z**2/total
    centre = (p + z**2/(2*total)) / denominator
    adjustment = z * np.sqrt((p*(1-p) + z**2/(4*total))/total) / denominator
    return p, centre - adjustment, centre + adjustment

def create_success_rate_comparison(output_dir: Path):
    """
    Create a single figure with 3 subplots showing success rates
    with proper confidence intervals
    """
    # Load data
    df = pd.read_csv('results/processed/summary.csv')
    
    # Create figure with 3 subplots
    fig, axes = plt.subplots(1, 3, figsize=(7.5, 2.5))
    
    # Define total attempts per config (all should have 5 seeds attempted)
    ATTEMPTS_PER_CONFIG = 5
    
    # ===== Subplot 1: By Network Profile =====
    ax = axes[0]
    net_data = []
    for net in ['NET0', 'NET2']:
        success = len(df[df['net_profile'] == net])
        # Each network has 4 sec × 2 data × 5 seeds = 40 configs attempted
        total = 40 if net in ['NET0', 'NET2'] else 0
        rate, ci_low, ci_high = wilson_ci(success, total)
        net_data.append({'profile': net, 'rate': rate*100, 
                        'ci_low': ci_low*100, 'ci_high': ci_high*100,
                        'success': success, 'total': total})
    
    net_df = pd.DataFrame(net_data)
    x_pos = np.arange(len(net_df))
    bars = ax.bar(x_pos, net_df['rate'], color=['#377eb8', '#ff7f00'], 
                   edgecolor='black', linewidth=0.8, alpha=0.85)
    
    # Add error bars (CI)
    errors = [net_df['rate'] - net_df['ci_low'], 
              net_df['ci_high'] - net_df['rate']]
    ax.errorbar(x_pos, net_df['rate'], yerr=errors, fmt='none', 
                ecolor='black', capsize=3, linewidth=1.2)
    
    # Add count labels on bars
    for i, (idx, row) in enumerate(net_df.iterrows()):
        ax.text(i, row['rate'] + 5, f"{row['success']}/{row['total']}", 
               ha='center', va='bottom', fontsize=7, fontweight='bold')
    
    ax.set_ylabel('Success Rate (%)', fontweight='bold')
    ax.set_xlabel('Network Profile', fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(net_df['profile'])
    ax.set_ylim(0, 105)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_title('(a) By Network', fontweight='bold')
    
    # ===== Subplot 2: By Security Configuration =====
    ax = axes[1]
    sec_data = []
    for sec in ['SEC0', 'SEC1', 'SEC2', 'SEC3']:
        success = len(df[df['sec_level'] == sec])
        # Each security has 2 net × 2 data × 5 seeds = 20 configs
        total = 20
        rate, ci_low, ci_high = wilson_ci(success, total)
        sec_data.append({'security': sec, 'rate': rate*100,
                        'ci_low': ci_low*100, 'ci_high': ci_high*100,
                        'success': success, 'total': total})
    
    sec_df = pd.DataFrame(sec_data)
    x_pos = np.arange(len(sec_df))
    colors = ['#377eb8', '#ff7f00', '#4daf4a', '#e41a1c']
    bars = ax.bar(x_pos, sec_df['rate'], color=colors, 
                   edgecolor='black', linewidth=0.8, alpha=0.85)
    
    # Add error bars
    errors = [sec_df['rate'] - sec_df['ci_low'],
              sec_df['ci_high'] - sec_df['rate']]
    ax.errorbar(x_pos, sec_df['rate'], yerr=errors, fmt='none',
                ecolor='black', capsize=3, linewidth=1.2)
    
    # Add count labels
    for i, (idx, row) in enumerate(sec_df.iterrows()):
        ax.text(i, row['rate'] + 5, f"{row['success']}/{row['total']}",
               ha='center', va='bottom', fontsize=7, fontweight='bold')
    
    ax.set_ylabel('Success Rate (%)', fontweight='bold')
    ax.set_xlabel('Security Configuration', fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(sec_df['security'])
    ax.set_ylim(0, 105)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_title('(b) By Security', fontweight='bold')
    
    # ===== Subplot 3: By Data Distribution =====
    ax = axes[2]
    data_dist_data = []
    for iid_val, label in [(True, 'IID'), (False, 'Non-IID')]:
        success = len(df[df['iid'] == iid_val])
        # Each data dist has 2 net × 4 sec × 5 seeds = 40 configs
        total = 40
        rate, ci_low, ci_high = wilson_ci(success, total)
        data_dist_data.append({'distribution': label, 'rate': rate*100,
                              'ci_low': ci_low*100, 'ci_high': ci_high*100,
                              'success': success, 'total': total})
    
    dist_df = pd.DataFrame(data_dist_data)
    x_pos = np.arange(len(dist_df))
    bars = ax.bar(x_pos, dist_df['rate'], color=['#4daf4a', '#984ea3'],
                   edgecolor='black', linewidth=0.8, alpha=0.85)
    
    # Add error bars
    errors = [dist_df['rate'] - dist_df['ci_low'],
              dist_df['ci_high'] - dist_df['rate']]
    ax.errorbar(x_pos, dist_df['rate'], yerr=errors, fmt='none',
                ecolor='black', capsize=3, linewidth=1.2)
    
    # Add count labels
    for i, (idx, row) in enumerate(dist_df.iterrows()):
        ax.text(i, row['rate'] + 5, f"{row['success']}/{row['total']}",
               ha='center', va='bottom', fontsize=7, fontweight='bold')
    
    ax.set_ylabel('Success Rate (%)', fontweight='bold')
    ax.set_xlabel('Data Distribution', fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(dist_df['distribution'])
    ax.set_ylim(0, 105)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_title('(c) By Data Distribution', fontweight='bold')
    
    plt.tight_layout()
    
    # Save figure
    output_file = output_dir / 'success_rates_combined.pdf'
    fig.savefig(output_file, format='pdf', bbox_inches='tight', dpi=300)
    print(f"✅ Saved: {output_file}")
    
    output_file_png = output_dir / 'success_rates_combined.png'
    fig.savefig(output_file_png, format='png', bbox_inches='tight', dpi=300)
    print(f"✅ Saved: {output_file_png}")
    
    plt.close()

if __name__ == '__main__':
    output_dir = Path('results/figures/publication')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating success rate comparison figure...")
    create_success_rate_comparison(output_dir)
    print("✅ Done!")
