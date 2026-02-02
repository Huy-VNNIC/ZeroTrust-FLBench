#!/usr/bin/env python3
"""
Comprehensive analysis of ZeroTrust FL experiment results
Generates success rate reports and visualizations for paper
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import glob
from collections import defaultdict
import numpy as np

def analyze_experiments():
    """Analyze all completed experiments and generate comprehensive report"""
    
    results_dir = Path("results/raw")
    results = []
    
    print("🔍 Scanning experiment results...")
    
    # Scan all experiment directories
    for exp_dir in results_dir.glob("202*"):
        if not exp_dir.is_dir():
            continue
            
        metadata_file = exp_dir / "metadata.json"
        if not metadata_file.exists():
            continue
            
        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            # Parse experiment info from directory name
            exp_name = exp_dir.name
            parts = exp_name.split('_')
            
            result = {
                'experiment_dir': str(exp_dir),
                'run_id': exp_name,
                'timestamp': metadata.get('timestamp'),
                'workload': metadata['config']['workload'],
                'data_dist': metadata['config']['data_distribution'],
                'num_clients': metadata['config']['num_clients'],
                'network': metadata['config']['network_profile'],
                'security': metadata['config']['security_config'], 
                'seed': metadata['config']['seed'],
                'success': True,  # If metadata exists, experiment completed
            }
            
            # Check for actual FL results
            results_file = exp_dir / "fl_results.json"
            if results_file.exists():
                with open(results_file) as f:
                    fl_results = json.load(f)
                result['fl_accuracy'] = fl_results.get('final_accuracy', 0)
                result['fl_rounds'] = fl_results.get('num_rounds', 0)
                result['convergence_time'] = fl_results.get('total_time', 0)
            else:
                result['fl_accuracy'] = None
                result['fl_rounds'] = None  
                result['convergence_time'] = None
                
            results.append(result)
            
        except Exception as e:
            print(f"❌ Error processing {exp_dir}: {e}")
            
    df = pd.DataFrame(results)
    print(f"✅ Found {len(df)} completed experiments")
    
    return df

def generate_success_rate_report(df):
    """Generate comprehensive success rate analysis"""
    
    print("\n📊 SUCCESS RATE ANALYSIS")
    print("=" * 50)
    
    total_expected = 80  # 2 datasets × 2 data_dist × 5 seeds × 2 networks × 4 security
    total_completed = len(df)
    
    print(f"Total Expected: {total_expected}")
    print(f"Total Completed: {total_completed}")
    print(f"Success Rate: {total_completed/total_expected*100:.1f}%")
    
    # By network profile
    print("\n📡 SUCCESS BY NETWORK PROFILE:")
    net_stats = df.groupby('network').size()
    for net, count in net_stats.items():
        print(f"  {net}: {count} experiments ({count/40*100:.1f}%)")
    
    # By security level  
    print("\n🔒 SUCCESS BY SECURITY LEVEL:")
    sec_stats = df.groupby('security').size()
    for sec, count in sec_stats.items():
        print(f"  {sec}: {count} experiments ({count/20*100:.1f}%)")
        
    # By data distribution
    print("\n📊 SUCCESS BY DATA DISTRIBUTION:")
    dist_stats = df.groupby('data_dist').size()
    for dist, count in dist_stats.items():
        print(f"  {dist}: {count} experiments ({count/40*100:.1f}%)")
    
    # Cross analysis: Network vs Security
    print("\n🔍 DETAILED SUCCESS MATRIX:")
    cross_tab = pd.crosstab(df['network'], df['security'], margins=True)
    print(cross_tab)
    
    return {
        'total_expected': total_expected,
        'total_completed': total_completed, 
        'success_rate': total_completed/total_expected,
        'by_network': net_stats.to_dict(),
        'by_security': sec_stats.to_dict(),
        'by_data_dist': dist_stats.to_dict(),
        'cross_matrix': cross_tab
    }

def create_visualizations(df, stats):
    """Create publication-quality visualizations"""
    
    print("\n📈 Generating visualizations...")
    
    # Set publication style
    plt.style.use('default')
    sns.set_palette("husl")
    fig_dir = Path("results/figures/publication")
    fig_dir.mkdir(parents=True, exist_ok=True)
    
    # Figure 1: Success Rate by Network Profile  
    plt.figure(figsize=(10, 6))
    net_data = pd.Series(stats['by_network'])
    bars = plt.bar(net_data.index, net_data.values, alpha=0.8, edgecolor='black')
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    plt.title('Experiment Success Rate by Network Profile', fontsize=14, fontweight='bold')
    plt.xlabel('Network Profile', fontsize=12)
    plt.ylabel('Number of Successful Experiments', fontsize=12)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(fig_dir / 'success_by_network.png', dpi=300, bbox_inches='tight')
    plt.savefig(fig_dir / 'success_by_network.pdf', bbox_inches='tight')
    plt.close()
    
    # Figure 2: Success Rate by Security Level
    plt.figure(figsize=(10, 6)) 
    sec_data = pd.Series(stats['by_security'])
    bars = plt.bar(sec_data.index, sec_data.values, alpha=0.8, edgecolor='black', color='orange')
    
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    plt.title('Experiment Success Rate by Security Configuration', fontsize=14, fontweight='bold')
    plt.xlabel('Security Configuration', fontsize=12)  
    plt.ylabel('Number of Successful Experiments', fontsize=12)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(fig_dir / 'success_by_security.png', dpi=300, bbox_inches='tight')
    plt.savefig(fig_dir / 'success_by_security.pdf', bbox_inches='tight')
    plt.close()
    
    # Figure 3: Cross-Matrix Heatmap
    plt.figure(figsize=(8, 6))
    cross_data = pd.crosstab(df['network'], df['security'])
    sns.heatmap(cross_data, annot=True, fmt='d', cmap='Blues', 
                cbar_kws={'label': 'Number of Experiments'})
    plt.title('Experiment Success Matrix: Network × Security', fontsize=14, fontweight='bold')
    plt.xlabel('Security Configuration', fontsize=12)
    plt.ylabel('Network Profile', fontsize=12)
    plt.tight_layout()
    plt.savefig(fig_dir / 'success_matrix_heatmap.png', dpi=300, bbox_inches='tight')
    plt.savefig(fig_dir / 'success_matrix_heatmap.pdf', bbox_inches='tight')
    plt.close()
    
    # Figure 4: Data Distribution Comparison
    plt.figure(figsize=(8, 6))
    dist_data = pd.Series(stats['by_data_dist'])
    bars = plt.bar(dist_data.index, dist_data.values, alpha=0.8, edgecolor='black', color='green')
    
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    plt.title('Experiment Success Rate by Data Distribution', fontsize=14, fontweight='bold')
    plt.xlabel('Data Distribution Type', fontsize=12)
    plt.ylabel('Number of Successful Experiments', fontsize=12) 
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(fig_dir / 'success_by_data_dist.png', dpi=300, bbox_inches='tight')
    plt.savefig(fig_dir / 'success_by_data_dist.pdf', bbox_inches='tight')
    plt.close()
    
    print(f"✅ Visualizations saved to {fig_dir}")
    
def generate_summary_report(df, stats):
    """Generate comprehensive summary for paper"""
    
    report_file = Path("results/EXPERIMENT_SUMMARY.md")
    
    with open(report_file, 'w') as f:
        f.write("# ZeroTrust FL Experiments - Comprehensive Results\n\n")
        f.write(f"**Generated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write(f"- **Total Experiments Planned**: {stats['total_expected']}\n")
        f.write(f"- **Total Experiments Completed**: {stats['total_completed']}\n") 
        f.write(f"- **Overall Success Rate**: {stats['success_rate']*100:.1f}%\n\n")
        
        f.write("## Experimental Matrix\n\n")
        f.write("| Parameter | Values |\n")
        f.write("|-----------|--------|\n")
        f.write("| Dataset | MNIST |\n")
        f.write("| Data Distribution | IID, Non-IID |\n")
        f.write("| Network Profiles | NET0 (baseline), NET2 (emulated) |\n")
        f.write("| Security Levels | SEC0 (baseline), SEC1 (NetworkPolicy), SEC2 (mTLS), SEC3 (combined) |\n")
        f.write("| Seeds per Config | 0, 1, 2, 3, 4 |\n")
        f.write("| Total Combinations | 2 × 2 × 4 × 5 = 80 experiments |\n\n")
        
        f.write("## Success Rate Analysis\n\n")
        f.write("### By Network Profile\n")
        for net, count in stats['by_network'].items():
            f.write(f"- **{net}**: {count} experiments ({count/40*100:.1f}%)\n")
        
        f.write("\n### By Security Level\n")
        for sec, count in stats['by_security'].items():
            f.write(f"- **{sec}**: {count} experiments ({count/20*100:.1f}%)\n")
            
        f.write("\n### By Data Distribution\n")
        for dist, count in stats['by_data_dist'].items():
            f.write(f"- **{dist}**: {count} experiments ({count/40*100:.1f}%)\n")
        
        f.write("\n## Cross-Analysis Matrix\n\n")
        f.write("```\n")
        f.write(str(stats['cross_matrix']))
        f.write("\n```\n\n")
        
        f.write("## Key Findings\n\n")
        
        # Analyze NET0 vs NET2 success
        net0_success = stats['by_network'].get('NET0', 0)
        net2_success = stats['by_network'].get('NET2', 0)
        
        if net0_success > net2_success:
            f.write(f"- **Network Impact**: NET0 (baseline) achieved higher success rate ({net0_success} vs {net2_success}), indicating network emulation introduces additional complexity\n")
        else:
            f.write(f"- **Network Impact**: Both network profiles achieved similar success rates (NET0: {net0_success}, NET2: {net2_success})\n")
            
        # Find best/worst security configs
        best_sec = max(stats['by_security'].items(), key=lambda x: x[1])
        worst_sec = min(stats['by_security'].items(), key=lambda x: x[1])
        
        f.write(f"- **Security Impact**: {best_sec[0]} achieved highest success ({best_sec[1]} experiments), {worst_sec[0]} achieved lowest ({worst_sec[1]} experiments)\n")
        
        f.write("\n## Files Generated\n\n")
        f.write("- `results/figures/publication/` - All visualization figures\n")
        f.write("- `results/raw/` - Raw experiment data and metadata\n") 
        f.write("- `results/EXPERIMENT_SUMMARY.md` - This comprehensive report\n\n")
        
        f.write("## Next Steps for Paper\n\n")
        f.write("1. **Performance Analysis**: Parse FL accuracy and convergence metrics from successful experiments\n")
        f.write("2. **Statistical Testing**: Compare security configurations with appropriate statistical tests\n")
        f.write("3. **Figure Integration**: Include generated visualizations in paper figures\n")
        f.write("4. **Discussion Points**: Address network emulation impact and security trade-offs\n")

    print(f"✅ Comprehensive report saved to {report_file}")

def main():
    """Main analysis pipeline"""
    
    print("🚀 Starting comprehensive experiment analysis...\n")
    
    # Analyze completed experiments
    df = analyze_experiments()
    
    if len(df) == 0:
        print("❌ No completed experiments found!")
        return
    
    # Generate statistics
    stats = generate_success_rate_report(df)
    
    # Create visualizations
    create_visualizations(df, stats)
    
    # Generate summary report
    generate_summary_report(df, stats)
    
    print(f"\n🎉 Analysis complete!")
    print(f"📊 Found {len(df)} successful experiments out of 80 planned")
    print(f"📈 Success rate: {stats['success_rate']*100:.1f}%")
    print(f"📁 Results saved in results/figures/publication/")
    print(f"📄 Summary report: results/EXPERIMENT_SUMMARY.md")

if __name__ == "__main__":
    main()