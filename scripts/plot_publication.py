#!/usr/bin/env python3
"""
Generate publication-ready figures for ZeroTrust-FLBench paper

Figures:
1. System overview (FL on K8s with security configs)
2. Heatmap: p99 latency (SEC × NET)
3. ECDF: Round latency distribution per SEC level
4. Bar chart: TTA comparison (mean + 95% CI)
5. Line plot: Accuracy convergence
6. Bar chart: Failure rate per config
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import seaborn as sns
from scipy import stats

# Publication style settings
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman'],
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.titlesize': 12,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1,
    'axes.linewidth': 0.8,
    'grid.linewidth': 0.5,
    'lines.linewidth': 1.5,
    'patch.linewidth': 0.8,
})

# Color palette (colorblind-friendly)
COLORS = {
    'SEC0': '#377eb8',  # Blue
    'SEC1': '#ff7f00',  # Orange
    'SEC2': '#4daf4a',  # Green
    'SEC3': '#e41a1c',  # Red
}

SEC_LABELS = {
    'SEC0': 'Baseline',
    'SEC1': 'NetworkPolicy',
    'SEC2': 'mTLS',
    'SEC3': 'NP+mTLS',
}


def set_figure_size(width_cm=17.8, height_cm=8):
    """Set figure size in cm (for two-column layout)"""
    width_inch = width_cm / 2.54
    height_inch = height_cm / 2.54
    return (width_inch, height_inch)


def save_figure(fig, output_path, formats=['pdf', 'png']):
    """Save figure in multiple formats"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    for fmt in formats:
        save_path = output_path.with_suffix(f'.{fmt}')
        fig.savefig(save_path, format=fmt, bbox_inches='tight')
        print(f"✅ Saved: {save_path}")


def fig1_system_overview(output_dir: Path):
    """
    Figure 1: ZeroTrust-FLBench System Overview
    Grid-based layout - ZERO overlaps guaranteed
    """
    # Clear font settings
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'DejaVu Sans', 'Liberation Sans'],
        'font.size': 8
    })
    
    # Very large figure with clear grid
    fig, ax = plt.subplots(figsize=set_figure_size(20, 16))  
    ax.set_xlim(0, 16)  
    ax.set_ylim(0, 14)  
    ax.axis('off')
    
    # === ROW 1: TITLE (y=13) ===
    ax.text(8, 13, 'ZeroTrust-FLBench System Architecture',
            ha='center', fontsize=14, fontweight='bold')
    
    # === ROW 2: MAIN COMPONENTS (y=6-12) ===
    
    # LEFT COLUMN: FL Clients (x=0-3, y=6-12)
    ax.text(1.5, 11.5, 'FL Clients', ha='center', fontsize=11, fontweight='bold')
    client_positions = [(1.5, 10.5), (1.5, 9.5), (1.5, 8.5), (1.5, 7.5), (1.5, 6.5)]
    
    for i, (x, y) in enumerate(client_positions):
        box = FancyBboxPatch((x-0.8, y-0.2), 1.6, 0.4,
                             boxstyle="round,pad=0.05",
                             edgecolor='black', facecolor='#e0f2ff',
                             linewidth=1.2)
        ax.add_patch(box)
        ax.text(x, y, f'Client {i+1}', ha='center', va='center', fontsize=9, fontweight='bold')
    
    # CENTER COLUMN: Kubernetes (x=4-12, y=6-12)
    # Kubernetes container
    k8s_box = FancyBboxPatch((4, 6), 8, 6,
                             boxstyle="round,pad=0.1",
                             edgecolor='#4169E1', facecolor='#f8f9ff',
                             linewidth=2.5, linestyle='--')
    ax.add_patch(k8s_box)
    ax.text(8, 11.5, 'Kubernetes Cluster', ha='center', fontsize=11, 
            fontweight='bold', color='#4169E1')
    
    # FL Server inside K8s (top area)
    server_box = FancyBboxPatch((5.5, 9.5), 3, 1,
                                boxstyle="round,pad=0.08",
                                edgecolor='black', facecolor='#ffe0e0',
                                linewidth=1.8)
    ax.add_patch(server_box)
    ax.text(7, 10, 'FL Server', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(7, 9.7, '(Aggregator)', ha='center', va='center', fontsize=8)
    
    # Client Pods inside K8s (bottom area) 
    pod_positions = [(5, 7.5), (7, 7.5), (9, 7.5)]
    for i, (x, y) in enumerate(pod_positions):
        pod_box = FancyBboxPatch((x-0.6, y-0.4), 1.2, 0.8,
                                 boxstyle="round,pad=0.05",
                                 edgecolor='black', facecolor='#e0f7ff',
                                 linewidth=1.2)
        ax.add_patch(pod_box)
        ax.text(x, y+0.1, f'Pod {i+1}', ha='center', va='center', fontsize=8, fontweight='bold')
        ax.text(x, y-0.2, 'Client', ha='center', va='center', fontsize=7)
    
    # RIGHT COLUMN: Security Levels (x=13-16, y=6-12)
    ax.text(14.5, 11.5, 'Security', ha='center', fontsize=11, fontweight='bold')
    ax.text(14.5, 11.2, 'Levels', ha='center', fontsize=11, fontweight='bold')
    
    sec_configs = ['SEC0', 'SEC1', 'SEC2', 'SEC3']
    sec_names = ['Baseline', 'NetworkPolicy', 'mTLS', 'Combined']
    colors = ['#377eb8', '#ff7f00', '#4daf4a', '#e41a1c']
    
    for i, (sec, name, color) in enumerate(zip(sec_configs, sec_names, colors)):
        y = 10.2 - i*0.8
        sec_box = FancyBboxPatch((13.2, y-0.25), 2.6, 0.5,
                                 boxstyle="round,pad=0.05",
                                 edgecolor=color, facecolor='white',
                                 linewidth=2)
        ax.add_patch(sec_box)
        ax.text(14.5, y+0.05, sec, ha='center', va='center', fontsize=8, 
               color=color, fontweight='bold')
        ax.text(14.5, y-0.15, name, ha='center', va='center', fontsize=7, color=color)
    
    # === ROW 3: NETWORK PROFILES (y=2-4) ===
    ax.text(8, 4.5, 'Network Profiles', ha='center', fontsize=11, fontweight='bold')
    
    net_configs = ['NET0', 'NET2', 'NET4'] 
    net_latencies = ['0ms', '50ms', '150ms']
    net_x_positions = [5, 8, 11]
    
    for i, (net, lat, x) in enumerate(zip(net_configs, net_latencies, net_x_positions)):
        net_box = FancyBboxPatch((x-1, 3), 2, 0.8,
                                 boxstyle="round,pad=0.05",
                                 edgecolor='#666', facecolor='#fff8e0',
                                 linewidth=1.5)
        ax.add_patch(net_box)
        ax.text(x, 3.5, net, ha='center', va='center', fontsize=9, fontweight='bold')
        ax.text(x, 3.2, f'({lat})', ha='center', va='center', fontsize=8)
    
    # === ARROWS ===
    # Clients to K8s - ALL 5 clients connect
    for _, client_y in client_positions:  # All 5 clients
        arrow = FancyArrowPatch((2.4, client_y), (3.9, client_y),
                               arrowstyle='->', mutation_scale=15,
                               linewidth=1.8, color='#333')
        ax.add_patch(arrow)
    
    # Server to Pods (inside K8s)
    for pod_x, pod_y in pod_positions:
        arrow = FancyArrowPatch((7, 9.4), (pod_x, pod_y+0.4),
                               arrowstyle='<->', mutation_scale=12,
                               linewidth=1.2, color='#666')
        ax.add_patch(arrow)
    
    save_figure(fig, output_dir / 'fig1_system_overview')
    plt.close()


def fig2_heatmap_latency(summary_df: pd.DataFrame, output_dir: Path):
    """
    Figure 2: Heatmap of p99 round latency (SEC × NET)
    Separate subplots for IID and Non-IID
    """
    fig, axes = plt.subplots(1, 2, figsize=set_figure_size(17.8, 7))
    
    for idx, (iid_val, ax) in enumerate(zip([True, False], axes)):
        df_filtered = summary_df[summary_df['iid'] == iid_val]
        
        # Pivot for heatmap
        pivot = df_filtered.pivot_table(
            values='p99_round',
            index='sec_level',
            columns='net_profile',
            aggfunc='mean'
        )
        
        # Reorder
        sec_order = ['SEC0', 'SEC1', 'SEC2', 'SEC3']
        net_order = ['NET0', 'NET2', 'NET4']
        pivot = pivot.reindex(index=sec_order, columns=net_order)
        
        # Plot heatmap
        sns.heatmap(pivot, annot=True, fmt='.1f', cmap='YlOrRd',
                   cbar_kws={'label': 'p99 Latency (s)'},
                   linewidths=0.5, linecolor='gray',
                   ax=ax, vmin=0, vmax=pivot.max().max()*1.1)
        
        ax.set_title(f'{"IID" if iid_val else "Non-IID"} Data Split',
                    fontweight='bold')
        ax.set_xlabel('Network Profile', fontweight='bold')
        ax.set_ylabel('Security Config', fontweight='bold')
        
        # Customize labels
        ax.set_yticklabels([SEC_LABELS.get(s, s) for s in sec_order],
                          rotation=0)
    
    plt.tight_layout()
    save_figure(fig, output_dir / 'fig2_heatmap_p99_latency')
    plt.close()


def fig3_ecdf_latency(rounds_df: pd.DataFrame, output_dir: Path):
    """
    Figure 3: ECDF of round latency per SEC level (NET0 vs NET2)
    """
    fig, axes = plt.subplots(1, 2, figsize=set_figure_size(17.8, 6.5))
    
    for idx, (net, ax) in enumerate(zip(['NET0', 'NET2'], axes)):
        df_filtered = rounds_df[rounds_df['run_id'].str.contains(net)]
        
        for sec_level in ['SEC0', 'SEC1', 'SEC2', 'SEC3']:
            durations = df_filtered[df_filtered['run_id'].str.contains(sec_level)]['duration'].dropna()
            
            if len(durations) > 0:
                sorted_data = np.sort(durations)
                ecdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
                
                ax.plot(sorted_data, ecdf,
                       label=SEC_LABELS[sec_level],
                       color=COLORS[sec_level],
                       linewidth=2)
        
        ax.set_xlabel('Round Duration (seconds)', fontweight='bold')
        ax.set_ylabel('Cumulative Probability', fontweight='bold')
        ax.set_title(f'{net} Network Profile', fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='lower right', frameon=True)
        ax.set_xlim(left=0)
        ax.set_ylim([0, 1])
    
    plt.tight_layout()
    save_figure(fig, output_dir / 'fig3_ecdf_latency')
    plt.close()


def fig4_tta_comparison(summary_df: pd.DataFrame, output_dir: Path):
    """
    Figure 4: Time-to-Accuracy comparison (mean + 95% CI)
    """
    fig, ax = plt.subplots(figsize=set_figure_size(17.8, 7))
    
    # Prepare data
    metrics = []
    for sec in ['SEC0', 'SEC1', 'SEC2', 'SEC3']:
        for net in ['NET0', 'NET2']:
            df_filtered = summary_df[
                (summary_df['sec_level'] == sec) &
                (summary_df['net_profile'] == net)
            ]
            
            tta_values = df_filtered['tta_95'].dropna()
            if len(tta_values) > 0:
                mean_tta = tta_values.mean()
                ci = stats.t.interval(0.95, len(tta_values)-1,
                                     loc=mean_tta,
                                     scale=stats.sem(tta_values))
                err = mean_tta - ci[0]
                
                metrics.append({
                    'sec': sec,
                    'net': net,
                    'mean': mean_tta,
                    'err': err
                })
    
    df_plot = pd.DataFrame(metrics)
    
    # Plot grouped bar chart
    x = np.arange(len(['SEC0', 'SEC1', 'SEC2', 'SEC3']))
    width = 0.35
    
    for i, net in enumerate(['NET0', 'NET2']):
        df_net = df_plot[df_plot['net'] == net]
        means = [df_net[df_net['sec'] == s]['mean'].values[0] if len(df_net[df_net['sec'] == s]) > 0 else 0
                for s in ['SEC0', 'SEC1', 'SEC2', 'SEC3']]
        errs = [df_net[df_net['sec'] == s]['err'].values[0] if len(df_net[df_net['sec'] == s]) > 0 else 0
               for s in ['SEC0', 'SEC1', 'SEC2', 'SEC3']]
        
        ax.bar(x + i*width, means, width, yerr=errs,
              label=net, capsize=4, alpha=0.8,
              color='#377eb8' if net == 'NET0' else '#ff7f00')
    
    ax.set_xlabel('Security Configuration', fontweight='bold')
    ax.set_ylabel('Time to 95% Accuracy (seconds)', fontweight='bold')
    ax.set_title('TTA Comparison (Mean ± 95% CI)', fontweight='bold')
    ax.set_xticks(x + width / 2)
    ax.set_xticklabels([SEC_LABELS[s] for s in ['SEC0', 'SEC1', 'SEC2', 'SEC3']])
    ax.legend(title='Network', frameon=True)
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    save_figure(fig, output_dir / 'fig4_tta_comparison')
    plt.close()


def fig5_accuracy_convergence(rounds_df: pd.DataFrame, output_dir: Path):
    """
    Figure 5: Accuracy convergence across rounds
    """
    fig, axes = plt.subplots(2, 2, figsize=set_figure_size(17.8, 12))
    axes = axes.flatten()
    
    sec_levels = ['SEC0', 'SEC1', 'SEC2', 'SEC3']
    
    for idx, (sec, ax) in enumerate(zip(sec_levels, axes)):
        for net in ['NET0', 'NET2']:
            df_filtered = rounds_df[
                rounds_df['run_id'].str.contains(f'{sec}_{net}')
            ].sort_values('round_id')
            
            if len(df_filtered) > 0:
                # Group by round and compute mean
                grouped = df_filtered.groupby('round_id')['accuracy'].agg(['mean', 'std'])
                
                ax.plot(grouped.index, grouped['mean'],
                       label=net,
                       linewidth=2,
                       color='#377eb8' if net == 'NET0' else '#ff7f00')
                
                # Shaded error region
                ax.fill_between(grouped.index,
                               grouped['mean'] - grouped['std'],
                               grouped['mean'] + grouped['std'],
                               alpha=0.2,
                               color='#377eb8' if net == 'NET0' else '#ff7f00')
        
        ax.set_xlabel('Round', fontweight='bold')
        ax.set_ylabel('Test Accuracy', fontweight='bold')
        ax.set_title(f'{SEC_LABELS[sec]}', fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(title='Network', frameon=True)
        ax.set_ylim([0.7, 1.0])
    
    plt.tight_layout()
    save_figure(fig, output_dir / 'fig5_accuracy_convergence')
    plt.close()


def fig6_failure_rate(summary_df: pd.DataFrame, output_dir: Path):
    """
    Figure 6: Failure rate per configuration
    """
    fig, ax = plt.subplots(figsize=set_figure_size(17.8, 6.5))
    
    # Prepare data
    failure_data = []
    for sec in ['SEC0', 'SEC1', 'SEC2', 'SEC3']:
        for net in ['NET0', 'NET2']:
            df_filtered = summary_df[
                (summary_df['sec_level'] == sec) &
                (summary_df['net_profile'] == net)
            ]
            
            if len(df_filtered) > 0:
                mean_failure = df_filtered['failure_rate'].mean()
                failure_data.append({
                    'config': f'{SEC_LABELS[sec]}\n{net}',
                    'failure_rate': mean_failure * 100  # Convert to percentage
                })
    
    df_plot = pd.DataFrame(failure_data)
    
    # Plot bar chart
    colors = [COLORS['SEC0'], COLORS['SEC0'],
             COLORS['SEC1'], COLORS['SEC1'],
             COLORS['SEC2'], COLORS['SEC2'],
             COLORS['SEC3'], COLORS['SEC3']]
    
    bars = ax.bar(range(len(df_plot)), df_plot['failure_rate'],
                  color=colors, alpha=0.8, edgecolor='black', linewidth=0.8)
    
    ax.set_xlabel('Configuration', fontweight='bold')
    ax.set_ylabel('Failure Rate (%)', fontweight='bold')
    ax.set_title('Failure Rate per Configuration', fontweight='bold')
    ax.set_xticks(range(len(df_plot)))
    ax.set_xticklabels(df_plot['config'], fontsize=8)
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim([0, max(df_plot['failure_rate']) * 1.2])
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.1f}%',
               ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    save_figure(fig, output_dir / 'fig6_failure_rate')
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Generate publication figures")
    parser.add_argument("--summary-csv", type=Path, required=True)
    parser.add_argument("--rounds-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results/figures/publication"))
    
    args = parser.parse_args()
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    print("📊 Generating publication figures...")
    
    # Generate Figure 1 (system overview - no data needed)
    print("\n🎨 Figure 1: System overview")
    fig1_system_overview(args.output_dir)
    
    # Load data
    print("\n📂 Loading data...")
    summary_df = pd.read_csv(args.summary_csv)
    rounds_df = pd.read_csv(args.rounds_csv)
    
    print(f"  Loaded {len(summary_df)} runs, {len(rounds_df)} rounds")
    
    # Generate figures 2-6
    print("\n🎨 Figure 2: Heatmap latency")
    fig2_heatmap_latency(summary_df, args.output_dir)
    
    print("\n🎨 Figure 3: ECDF latency")
    fig3_ecdf_latency(rounds_df, args.output_dir)
    
    print("\n🎨 Figure 4: TTA comparison")
    fig4_tta_comparison(summary_df, args.output_dir)
    
    print("\n🎨 Figure 5: Accuracy convergence")
    fig5_accuracy_convergence(rounds_df, args.output_dir)
    
    print("\n🎨 Figure 6: Failure rate")
    fig6_failure_rate(summary_df, args.output_dir)
    
    print("\n✅ All figures generated!")
    print(f"   Output: {args.output_dir}")


if __name__ == "__main__":
    main()
