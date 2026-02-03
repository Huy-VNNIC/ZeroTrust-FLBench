#!/usr/bin/env python3
"""
Generate PERFORMANCE OVERHEAD figures (NOT success rate)
Focus on metrics that show ACTUAL TRADE-OFFS
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import seaborn as sns

# IEEE style
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'DejaVu Sans'],
    'font.size': 8,
    'axes.labelsize': 9,
    'axes.titlesize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
})

def create_interaction_heatmaps(output_dir: Path):
    """
    Create Network × Security interaction heatmaps
    THIS is what reviewer wants to see!
    """
    df = pd.read_csv('results/processed/summary.csv')
    
    fig, axes = plt.subplots(1, 3, figsize=(7.5, 2.5))
    
    # ===== (a) P99 Latency =====
    ax = axes[0]
    pivot = df.pivot_table(values='p99_round', 
                          index='sec_level', 
                          columns='net_profile',
                          aggfunc='mean')
    
    sns.heatmap(pivot, annot=True, fmt='.1f', cmap='YlOrRd',
                cbar_kws={'label': 'P99 Latency (s)'},
                ax=ax, linewidths=0.5, linecolor='white')
    ax.set_title('(a) P99 Round Latency', fontweight='bold', pad=10)
    ax.set_xlabel('Network Profile', fontweight='bold')
    ax.set_ylabel('Security Config', fontweight='bold')
    
    # ===== (b) TTA (Time to 95% Accuracy) =====
    ax = axes[1]
    pivot_tta = df.pivot_table(values='tta_95',
                               index='sec_level',
                               columns='net_profile',
                               aggfunc='mean')
    
    sns.heatmap(pivot_tta, annot=True, fmt='.0f', cmap='RdYlGn_r',
                cbar_kws={'label': 'TTA (seconds)'},
                ax=ax, linewidths=0.5, linecolor='white')
    ax.set_title('(b) Time to 95% Accuracy', fontweight='bold', pad=10)
    ax.set_xlabel('Network Profile', fontweight='bold')
    ax.set_ylabel('')
    ax.set_yticklabels([])
    
    # ===== (c) Failure Rate per Round =====
    ax = axes[2]
    pivot_fail = df.pivot_table(values='failure_rate',
                                index='sec_level',
                                columns='net_profile',
                                aggfunc='mean') * 100  # Convert to %
    
    sns.heatmap(pivot_fail, annot=True, fmt='.2f', cmap='Reds',
                cbar_kws={'label': 'Failure Rate (%)'},
                ax=ax, linewidths=0.5, linecolor='white', vmin=0, vmax=2)
    ax.set_title('(c) Round Failure Rate', fontweight='bold', pad=10)
    ax.set_xlabel('Network Profile', fontweight='bold')
    ax.set_ylabel('')
    ax.set_yticklabels([])
    
    plt.tight_layout()
    
    # Save
    output_file = output_dir / 'performance_overhead_interaction.pdf'
    fig.savefig(output_file, format='pdf', bbox_inches='tight', dpi=300)
    print(f"✅ Saved: {output_file}")
    
    output_file_png = output_dir / 'performance_overhead_interaction.png'
    fig.savefig(output_file_png, format='png', bbox_inches='tight', dpi=300)
    print(f"✅ Saved: {output_file_png}")
    
    plt.close()
    
    # Print statistics for paper
    print("\n=== STATISTICS FOR PAPER ===")
    print(f"\nP99 Latency overhead (SEC3 vs SEC0 at NET0):")
    sec0_net0 = df[(df.sec_level=='SEC0') & (df.net_profile=='NET0')]['p99_round'].mean()
    sec3_net0 = df[(df.sec_level=='SEC3') & (df.net_profile=='NET0')]['p99_round'].mean()
    overhead = (sec3_net0 - sec0_net0) / sec0_net0 * 100
    print(f"  SEC0: {sec0_net0:.2f}s")
    print(f"  SEC3: {sec3_net0:.2f}s")
    print(f"  Overhead: {overhead:.1f}%")
    
    print(f"\nNetwork impact (NET2 vs NET0 at SEC0):")
    sec0_net0 = df[(df.sec_level=='SEC0') & (df.net_profile=='NET0')]['p99_round'].mean()
    sec0_net2 = df[(df.sec_level=='SEC0') & (df.net_profile=='NET2')]['p99_round'].mean()
    net_overhead = (sec0_net2 - sec0_net0) / sec0_net0 * 100
    print(f"  NET0: {sec0_net0:.2f}s")
    print(f"  NET2: {sec0_net2:.2f}s")
    print(f"  Overhead: {net_overhead:.1f}%")


def create_marginal_performance_bars(output_dir: Path):
    """
    Marginal performance comparison (with proper CI and sample sizes)
    """
    df = pd.read_csv('results/processed/summary.csv')
    
    fig, axes = plt.subplots(1, 3, figsize=(7.5, 2.2))
    
    # ===== (a) By Network =====
    ax = axes[0]
    net_stats = df.groupby('net_profile')['p99_round'].agg(['mean', 'std', 'count'])
    net_stats['se'] = net_stats['std'] / np.sqrt(net_stats['count'])
    net_stats['ci95'] = 1.96 * net_stats['se']
    
    x_pos = np.arange(len(net_stats))
    bars = ax.bar(x_pos, net_stats['mean'], 
                   color=['#377eb8', '#ff7f00'],
                   edgecolor='black', linewidth=0.8, alpha=0.85)
    ax.errorbar(x_pos, net_stats['mean'], yerr=net_stats['ci95'],
                fmt='none', ecolor='black', capsize=4, linewidth=1.5)
    
    # Add sample sizes
    for i, (idx, row) in enumerate(net_stats.iterrows()):
        ax.text(i, row['mean'] + row['ci95'] + 0.3,
               f"n={int(row['count'])}", 
               ha='center', fontsize=7, fontweight='bold')
    
    ax.set_ylabel('P99 Round Latency (s)', fontweight='bold')
    ax.set_xlabel('Network Profile', fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(net_stats.index)
    ax.set_title('(a) By Network', fontweight='bold')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # ===== (b) By Security =====
    ax = axes[1]
    sec_stats = df.groupby('sec_level')['p99_round'].agg(['mean', 'std', 'count'])
    sec_stats['se'] = sec_stats['std'] / np.sqrt(sec_stats['count'])
    sec_stats['ci95'] = 1.96 * sec_stats['se']
    
    x_pos = np.arange(len(sec_stats))
    colors = ['#377eb8', '#ff7f00', '#4daf4a', '#e41a1c']
    bars = ax.bar(x_pos, sec_stats['mean'],
                   color=colors, edgecolor='black',
                   linewidth=0.8, alpha=0.85)
    ax.errorbar(x_pos, sec_stats['mean'], yerr=sec_stats['ci95'],
                fmt='none', ecolor='black', capsize=4, linewidth=1.5)
    
    for i, (idx, row) in enumerate(sec_stats.iterrows()):
        ax.text(i, row['mean'] + row['ci95'] + 0.3,
               f"n={int(row['count'])}",
               ha='center', fontsize=7, fontweight='bold')
    
    ax.set_ylabel('P99 Round Latency (s)', fontweight='bold')
    ax.set_xlabel('Security Configuration', fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(sec_stats.index)
    ax.set_title('(b) By Security', fontweight='bold')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # ===== (c) By Data Distribution =====
    ax = axes[2]
    df['data_type'] = df['iid'].map({True: 'IID', False: 'Non-IID'})
    data_stats = df.groupby('data_type')['p99_round'].agg(['mean', 'std', 'count'])
    data_stats['se'] = data_stats['std'] / np.sqrt(data_stats['count'])
    data_stats['ci95'] = 1.96 * data_stats['se']
    
    x_pos = np.arange(len(data_stats))
    bars = ax.bar(x_pos, data_stats['mean'],
                   color=['#4daf4a', '#984ea3'],
                   edgecolor='black', linewidth=0.8, alpha=0.85)
    ax.errorbar(x_pos, data_stats['mean'], yerr=data_stats['ci95'],
                fmt='none', ecolor='black', capsize=4, linewidth=1.5)
    
    for i, (idx, row) in enumerate(data_stats.iterrows()):
        ax.text(i, row['mean'] + row['ci95'] + 0.3,
               f"n={int(row['count'])}",
               ha='center', fontsize=7, fontweight='bold')
    
    ax.set_ylabel('P99 Round Latency (s)', fontweight='bold')
    ax.set_xlabel('Data Distribution', fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(data_stats.index)
    ax.set_title('(c) By Data Distribution', fontweight='bold')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    
    output_file = output_dir / 'performance_marginal.pdf'
    fig.savefig(output_file, format='pdf', bbox_inches='tight', dpi=300)
    print(f"✅ Saved: {output_file}")
    
    plt.close()


if __name__ == '__main__':
    output_dir = Path('results/figures/publication')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating interaction heatmaps (Network × Security)...")
    create_interaction_heatmaps(output_dir)
    
    print("\nGenerating marginal performance bars...")
    create_marginal_performance_bars(output_dir)
    
    print("\n✅ All performance overhead figures generated!")
    print("\n📊 KEY POINT: Focus on OVERHEAD, not success rate")
    print("   All 80 experiments completed → 100% success")
    print("   → Paper analyzes PERFORMANCE COST of security controls")
