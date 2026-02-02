#!/usr/bin/env python3
"""
Generate sanity plots to validate experiment results before full matrix

Plots:
1. Accuracy vs Round (should be monotonic increasing)
2. Duration vs Round (should be stable, no huge outliers)
3. ECDF of Round Duration (visualize p50/p95/p99)
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def plot_accuracy_vs_round(rounds_df: pd.DataFrame, output_path: Path):
    """Plot accuracy progression over rounds"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for run_id in rounds_df["run_id"].unique():
        run_data = rounds_df[rounds_df["run_id"] == run_id].sort_values("round_id")
        ax.plot(run_data["round_id"], run_data["accuracy"], 
                marker='o', label=run_id, alpha=0.7)
    
    ax.set_xlabel("Round", fontsize=12)
    ax.set_ylabel("Test Accuracy", fontsize=12)
    ax.set_title("Accuracy vs Round (Sanity Check)", fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {output_path}")
    plt.close()


def plot_duration_vs_round(rounds_df: pd.DataFrame, output_path: Path):
    """Plot round duration over time"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for run_id in rounds_df["run_id"].unique():
        run_data = rounds_df[rounds_df["run_id"] == run_id].sort_values("round_id")
        run_data = run_data.dropna(subset=["duration"])
        ax.plot(run_data["round_id"], run_data["duration"], 
                marker='o', label=run_id, alpha=0.7)
    
    ax.set_xlabel("Round", fontsize=12)
    ax.set_ylabel("Duration (seconds)", fontsize=12)
    ax.set_title("Round Duration vs Round (Sanity Check)", fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Add median line
    all_durations = rounds_df["duration"].dropna()
    if len(all_durations) > 0:
        median = all_durations.median()
        ax.axhline(median, color='red', linestyle='--', linewidth=2, 
                   label=f'Median: {median:.1f}s')
        ax.legend()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {output_path}")
    plt.close()


def plot_ecdf_duration(rounds_df: pd.DataFrame, output_path: Path):
    """Plot ECDF of round durations"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    durations = rounds_df["duration"].dropna().sort_values()
    
    if len(durations) == 0:
        print("⚠️  No duration data to plot ECDF")
        return
    
    # Compute ECDF
    y = np.arange(1, len(durations) + 1) / len(durations)
    
    ax.plot(durations, y, linewidth=2, label="ECDF")
    
    # Mark percentiles
    p50 = durations.quantile(0.50)
    p95 = durations.quantile(0.95)
    p99 = durations.quantile(0.99)
    
    ax.axvline(p50, color='green', linestyle='--', linewidth=1.5, 
               label=f'p50: {p50:.1f}s')
    ax.axvline(p95, color='orange', linestyle='--', linewidth=1.5, 
               label=f'p95: {p95:.1f}s')
    ax.axvline(p99, color='red', linestyle='--', linewidth=1.5, 
               label=f'p99: {p99:.1f}s')
    
    ax.set_xlabel("Round Duration (seconds)", fontsize=12)
    ax.set_ylabel("Cumulative Probability", fontsize=12)
    ax.set_title("ECDF of Round Duration (Sanity Check)", fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {output_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Generate sanity check plots")
    parser.add_argument("--rounds-csv", type=Path, required=True, 
                       help="Path to rounds.csv from parse_logs.py")
    parser.add_argument("--output-dir", type=Path, required=True, 
                       help="Output directory for plots")
    
    args = parser.parse_args()
    
    if not args.rounds_csv.exists():
        print(f"❌ Error: {args.rounds_csv} not found")
        print("   Run parse_logs.py first to generate rounds.csv")
        sys.exit(1)
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print(f"Loading {args.rounds_csv}...")
    rounds_df = pd.read_csv(args.rounds_csv)
    
    print(f"Found {len(rounds_df)} rounds from {rounds_df['run_id'].nunique()} run(s)")
    
    # Generate plots
    plot_accuracy_vs_round(rounds_df, args.output_dir / "accuracy_vs_round.png")
    plot_duration_vs_round(rounds_df, args.output_dir / "duration_vs_round.png")
    plot_ecdf_duration(rounds_df, args.output_dir / "ecdf_duration.png")
    
    print("\n📊 Sanity plots complete!")
    print(f"   Check plots in: {args.output_dir}")
    print("\n🔍 Visual inspection checklist:")
    print("   [ ] Accuracy increases monotonically (or near-monotonic)")
    print("   [ ] Duration has no extreme outliers (>5x median)")
    print("   [ ] ECDF is smooth (no sudden jumps)")


if __name__ == "__main__":
    main()
