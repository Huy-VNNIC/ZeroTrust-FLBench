#!/usr/bin/env python3
"""
Performance analysis of ZeroTrust FL experiments
Analyzes FL accuracy, convergence, and performance metrics
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
from scipy import stats

def extract_fl_performance():
    """Extract FL performance metrics from completed experiments"""
    
    results_dir = Path("results/raw")
    performance_data = []
    
    print("🔍 Extracting FL performance data...")
    
    for exp_dir in results_dir.glob("202*"):
        if not exp_dir.is_dir():
            continue
            
        # Load metadata
        metadata_file = exp_dir / "metadata.json"
        if not metadata_file.exists():
            continue
            
        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            config = metadata['config']
            
            # Try to find FL results file
            fl_results_file = exp_dir / "fl_results.json"
            server_log = exp_dir / "server.log"
            
            # Extract performance metrics from available sources
            metrics = {
                'experiment': exp_dir.name,
                'network': config['network_profile'],
                'security': config['security_config'],
                'data_dist': config['data_distribution'],
                'seed': config['seed'],
                'timestamp': metadata['timestamp']
            }
            
            # Try FL results file first
            if fl_results_file.exists():
                with open(fl_results_file) as f:
                    fl_data = json.load(f)
                    
                metrics.update({
                    'final_accuracy': fl_data.get('final_accuracy', None),
                    'num_rounds': fl_data.get('num_rounds', None),
                    'convergence_time': fl_data.get('total_time', None),
                    'max_accuracy': fl_data.get('max_accuracy', None)
                })
            
            # If no FL results, try parsing server logs for accuracy
            elif server_log.exists():
                try:
                    accuracies = []
                    with open(server_log) as f:
                        for line in f:
                            if '"accuracy"' in line and 'round' in line:
                                # Try to parse JSON log line
                                try:
                                    log_data = json.loads(line)
                                    if 'accuracy' in log_data:
                                        accuracies.append(log_data['accuracy'])
                                except:
                                    # Try regex parsing if JSON fails
                                    import re
                                    acc_match = re.search(r'"accuracy":\s*([\d.]+)', line)
                                    if acc_match:
                                        accuracies.append(float(acc_match.group(1)))
                    
                    if accuracies:
                        metrics.update({
                            'final_accuracy': accuracies[-1] if accuracies else None,
                            'num_rounds': len(accuracies),
                            'max_accuracy': max(accuracies) if accuracies else None,
                            'convergence_time': None  # Can't extract from logs easily
                        })
                        
                except Exception as e:
                    print(f"  ⚠️ Error parsing server log {exp_dir}: {e}")
                    
            performance_data.append(metrics)
            
        except Exception as e:
            print(f"❌ Error processing {exp_dir}: {e}")
    
    df = pd.DataFrame(performance_data)
    print(f"✅ Extracted performance data from {len(df)} experiments")
    
    return df

def analyze_performance_metrics(df):
    """Analyze FL performance across different configurations"""
    
    print("\n📊 PERFORMANCE ANALYSIS")
    print("=" * 50)
    
    # Check if we have final_accuracy column
    if 'final_accuracy' not in df.columns:
        print("❌ No FL performance data found yet!")
        print("   This is expected if experiments just completed.")
        print("   FL results are typically generated after experiment completion.")
        return None
    
    # Filter experiments with valid accuracy data
    valid_acc = df[df['final_accuracy'].notna()]
    print(f"Experiments with accuracy data: {len(valid_acc)}")
    
    if len(valid_acc) == 0:
        print("❌ No experiments with accuracy data found")
        print("   FL accuracy parsing will be implemented in next phase")
        return None
    
    # Performance by network profile
    print("\n📡 PERFORMANCE BY NETWORK PROFILE:")
    net_perf = valid_acc.groupby('network')['final_accuracy'].agg(['mean', 'std', 'count'])
    for net, row in net_perf.iterrows():
        print(f"  {net}: {row['mean']:.4f} ± {row['std']:.4f} (n={row['count']})")
    
    # Performance by security level
    print("\n🔒 PERFORMANCE BY SECURITY LEVEL:")
    sec_perf = valid_acc.groupby('security')['final_accuracy'].agg(['mean', 'std', 'count'])
    for sec, row in sec_perf.iterrows():
        print(f"  {sec}: {row['mean']:.4f} ± {row['std']:.4f} (n={row['count']})")
    
    # Performance by data distribution
    print("\n📊 PERFORMANCE BY DATA DISTRIBUTION:")
    dist_perf = valid_acc.groupby('data_dist')['final_accuracy'].agg(['mean', 'std', 'count'])
    for dist, row in dist_perf.iterrows():
        print(f"  {dist}: {row['mean']:.4f} ± {row['std']:.4f} (n={row['count']})")
    
    # Statistical testing
    print("\n📈 STATISTICAL SIGNIFICANCE TESTING:")
    
    # Network comparison
    if len(valid_acc['network'].unique()) >= 2:
        net0_acc = valid_acc[valid_acc['network'] == 'NET0']['final_accuracy'].dropna()
        net2_acc = valid_acc[valid_acc['network'] == 'NET2']['final_accuracy'].dropna()
        
        if len(net0_acc) > 0 and len(net2_acc) > 0:
            t_stat, p_val = stats.ttest_ind(net0_acc, net2_acc)
            print(f"  Network (NET0 vs NET2): t={t_stat:.3f}, p={p_val:.4f}")
            if p_val < 0.05:
                print(f"    → Significant difference (α=0.05)")
            else:
                print(f"    → No significant difference")
    
    # Security comparison (baseline vs others)
    sec0_acc = valid_acc[valid_acc['security'] == 'SEC0']['final_accuracy'].dropna()
    other_acc = valid_acc[valid_acc['security'] != 'SEC0']['final_accuracy'].dropna()
    
    if len(sec0_acc) > 0 and len(other_acc) > 0:
        t_stat, p_val = stats.ttest_ind(sec0_acc, other_acc)
        print(f"  Security (SEC0 vs Others): t={t_stat:.3f}, p={p_val:.4f}")
        if p_val < 0.05:
            print(f"    → Security measures significantly impact accuracy")
        else:
            print(f"    → No significant impact of security measures")
    
    return {
        'by_network': net_perf,
        'by_security': sec_perf,
        'by_data_dist': dist_perf,
        'valid_experiments': len(valid_acc)
    }

def create_performance_visualizations(df, stats):
    """Create performance visualization figures for paper"""
    
    print("\n📈 Creating performance visualizations...")
    
    # Check if we have performance data
    if stats is None or 'final_accuracy' not in df.columns:
        print("⚠️  No FL performance data available for visualization yet")
        print("   Visualization will be generated once FL results are parsed")
        return
    
    valid_acc = df[df['final_accuracy'].notna()]
    if len(valid_acc) == 0:
        print("❌ No accuracy data available for visualization")
        return
    
    fig_dir = Path("results/figures/publication")
    fig_dir.mkdir(parents=True, exist_ok=True)
    
    # Figure 1: Accuracy by Network Profile
    plt.figure(figsize=(10, 6))
    
    net_data = []
    net_labels = []
    for net in valid_acc['network'].unique():
        net_acc = valid_acc[valid_acc['network'] == net]['final_accuracy']
        net_data.append(net_acc.values)
        net_labels.append(f"{net}\n(n={len(net_acc)})")
    
    box_plot = plt.boxplot(net_data, labels=net_labels, patch_artist=True)
    colors = ['lightblue', 'lightcoral']
    for patch, color in zip(box_plot['boxes'], colors[:len(box_plot['boxes'])]):
        patch.set_facecolor(color)
    
    plt.title('FL Accuracy by Network Profile', fontsize=14, fontweight='bold')
    plt.ylabel('Final Accuracy', fontsize=12)
    plt.xlabel('Network Profile', fontsize=12)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(fig_dir / 'fl_accuracy_by_network.png', dpi=300, bbox_inches='tight')
    plt.savefig(fig_dir / 'fl_accuracy_by_network.pdf', bbox_inches='tight')
    plt.close()
    
    # Figure 2: Accuracy by Security Level
    plt.figure(figsize=(12, 6))
    
    sec_data = []
    sec_labels = []
    for sec in sorted(valid_acc['security'].unique()):
        sec_acc = valid_acc[valid_acc['security'] == sec]['final_accuracy']
        sec_data.append(sec_acc.values)
        sec_labels.append(f"{sec}\n(n={len(sec_acc)})")
    
    box_plot = plt.boxplot(sec_data, labels=sec_labels, patch_artist=True)
    colors = ['lightgreen', 'lightblue', 'lightcoral', 'lightyellow']
    for patch, color in zip(box_plot['boxes'], colors[:len(box_plot['boxes'])]):
        patch.set_facecolor(color)
    
    plt.title('FL Accuracy by Security Configuration', fontsize=14, fontweight='bold')
    plt.ylabel('Final Accuracy', fontsize=12)
    plt.xlabel('Security Configuration', fontsize=12)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(fig_dir / 'fl_accuracy_by_security.png', dpi=300, bbox_inches='tight')
    plt.savefig(fig_dir / 'fl_accuracy_by_security.pdf', bbox_inches='tight')
    plt.close()
    
    # Figure 3: Combined Analysis - Network × Security Heatmap
    if len(valid_acc) > 10:  # Only if enough data
        plt.figure(figsize=(10, 8))
        
        pivot_data = valid_acc.groupby(['network', 'security'])['final_accuracy'].mean().unstack()
        sns.heatmap(pivot_data, annot=True, fmt='.4f', cmap='RdYlBu_r', 
                   cbar_kws={'label': 'Mean Final Accuracy'})
        
        plt.title('FL Accuracy Heatmap: Network × Security', fontsize=14, fontweight='bold')
        plt.xlabel('Security Configuration', fontsize=12)
        plt.ylabel('Network Profile', fontsize=12)
        plt.tight_layout()
        plt.savefig(fig_dir / 'fl_accuracy_heatmap.png', dpi=300, bbox_inches='tight')
        plt.savefig(fig_dir / 'fl_accuracy_heatmap.pdf', bbox_inches='tight')
        plt.close()
    
    # Figure 4: Data Distribution Comparison
    plt.figure(figsize=(10, 6))
    
    dist_data = []
    dist_labels = []
    for dist in valid_acc['data_dist'].unique():
        dist_acc = valid_acc[valid_acc['data_dist'] == dist]['final_accuracy']
        dist_data.append(dist_acc.values)
        dist_labels.append(f"{dist}\n(n={len(dist_acc)})")
    
    box_plot = plt.boxplot(dist_data, labels=dist_labels, patch_artist=True)
    colors = ['lightgreen', 'lightcoral']
    for patch, color in zip(box_plot['boxes'], colors[:len(box_plot['boxes'])]):
        patch.set_facecolor(color)
    
    plt.title('FL Accuracy by Data Distribution', fontsize=14, fontweight='bold')
    plt.ylabel('Final Accuracy', fontsize=12)
    plt.xlabel('Data Distribution Type', fontsize=12)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(fig_dir / 'fl_accuracy_by_distribution.png', dpi=300, bbox_inches='tight')
    plt.savefig(fig_dir / 'fl_accuracy_by_distribution.pdf', bbox_inches='tight')
    plt.close()
    
    print(f"✅ Performance visualizations saved to {fig_dir}")

def generate_performance_report(df, stats):
    """Generate detailed performance analysis report"""
    
    report_file = Path("results/PERFORMANCE_ANALYSIS.md")
    
    # Check if we have performance data
    has_acc_data = 'final_accuracy' in df.columns and df['final_accuracy'].notna().sum() > 0
    valid_acc = df[df['final_accuracy'].notna()] if has_acc_data else pd.DataFrame()
    
    with open(report_file, 'w') as f:
        f.write("# ZeroTrust FL Performance Analysis\n\n")
        f.write(f"**Generated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Performance Summary\n\n")
        if has_acc_data and len(valid_acc) > 0:
            f.write(f"- **Total Experiments with FL Results**: {len(valid_acc)}\n")
            f.write(f"- **Overall Mean Accuracy**: {valid_acc['final_accuracy'].mean():.4f} ± {valid_acc['final_accuracy'].std():.4f}\n")
            f.write(f"- **Accuracy Range**: {valid_acc['final_accuracy'].min():.4f} - {valid_acc['final_accuracy'].max():.4f}\n\n")
        else:
            f.write("- **No FL performance data available yet**\n\n")
            f.write("This is expected for recently completed experiments. FL performance analysis requires:\n")
            f.write("1. Server logs to be parsed for accuracy metrics\n")
            f.write("2. FL results JSON files to be generated\n") 
            f.write("3. Additional post-processing of experiment outputs\n\n")
            f.write("## Current Experiment Status\n\n")
            f.write(f"- **Total Experiments Completed**: {len(df)}\n")
            f.write(f"- **Experiments by Network**:\n")
            net_counts = df['network'].value_counts()
            for net, count in net_counts.items():
                f.write(f"  - {net}: {count} experiments\n")
            f.write(f"- **Experiments by Security**:\n") 
            sec_counts = df['security'].value_counts()
            for sec, count in sec_counts.items():
                f.write(f"  - {sec}: {count} experiments\n")
            return
        
        f.write("## Detailed Performance Analysis\n\n")
        
        if stats:
            f.write("### Network Profile Impact\n\n")
            for net, row in stats['by_network'].iterrows():
                f.write(f"- **{net}**: {row['mean']:.4f} ± {row['std']:.4f} (n={row['count']})\n")
            
            f.write("\n### Security Configuration Impact\n\n")
            for sec, row in stats['by_security'].iterrows():
                f.write(f"- **{sec}**: {row['mean']:.4f} ± {row['std']:.4f} (n={row['count']})\n")
                
            f.write("\n### Data Distribution Impact\n\n")
            for dist, row in stats['by_data_dist'].iterrows():
                f.write(f"- **{dist}**: {row['mean']:.4f} ± {row['std']:.4f} (n={row['count']})\n")
        
        f.write("\n## Key Insights for Paper\n\n")
        
        if len(valid_acc) > 0:
            # Network analysis
            net_stats = valid_acc.groupby('network')['final_accuracy'].mean()
            if 'NET0' in net_stats.index and 'NET2' in net_stats.index:
                if net_stats['NET0'] > net_stats['NET2']:
                    f.write("- **Network Emulation Impact**: Baseline network (NET0) achieves higher accuracy than emulated network (NET2), suggesting network constraints affect FL convergence\n")
                else:
                    f.write("- **Network Resilience**: FL performance remains stable under network emulation (NET2), indicating robustness to network constraints\n")
            
            # Security analysis
            sec_stats = valid_acc.groupby('security')['final_accuracy'].mean()
            sec0_acc = sec_stats.get('SEC0', 0)
            other_mean = sec_stats[sec_stats.index != 'SEC0'].mean()
            
            if sec0_acc > other_mean:
                f.write("- **Security Overhead**: Security measures (SEC1-SEC3) introduce performance overhead compared to baseline (SEC0)\n")
            else:
                f.write("- **Security Efficiency**: Security measures maintain comparable performance to baseline configuration\n")
                
            # Data distribution
            dist_stats = valid_acc.groupby('data_dist')['final_accuracy'].mean()
            if 'iid' in dist_stats.index and 'noniid' in dist_stats.index:
                if dist_stats['iid'] > dist_stats['noniid']:
                    f.write("- **Data Distribution Effect**: IID data distribution achieves higher accuracy than Non-IID, confirming expected FL behavior\n")
        
        f.write("\n## Recommendations\n\n")
        f.write("1. **Further Analysis**: Parse additional FL metrics (convergence rounds, training time) from server logs\n")
        f.write("2. **Statistical Testing**: Conduct comprehensive statistical comparison between configurations\n")
        f.write("3. **Performance Optimization**: Investigate specific security configurations that maintain high accuracy\n")
        f.write("4. **Network Analysis**: Detailed analysis of NET2 performance patterns and failure modes\n")
        
    print(f"✅ Performance report saved to {report_file}")

def main():
    """Main performance analysis pipeline"""
    
    print("🚀 Starting FL performance analysis...\n")
    
    # Extract performance data
    df = extract_fl_performance()
    
    if len(df) == 0:
        print("❌ No experiment data found!")
        return
    
    # Analyze performance
    stats = analyze_performance_metrics(df)
    
    # Create visualizations
    create_performance_visualizations(df, stats)
    
    # Generate detailed report
    generate_performance_report(df, stats)
    
    print(f"\n🎉 Performance analysis complete!")
    print(f"📊 Analyzed {len(df)} experiments")
    has_acc_data = 'final_accuracy' in df.columns and df['final_accuracy'].notna().sum() > 0
    if has_acc_data:
        valid_acc = df[df['final_accuracy'].notna()]
        print(f"📈 Found FL results in {len(valid_acc)} experiments")
    else:
        print(f"📈 FL accuracy data will be available after post-processing")
    print(f"📁 Performance figures saved to results/figures/publication/")
    print(f"📄 Performance report: results/PERFORMANCE_ANALYSIS.md")

if __name__ == "__main__":
    main()