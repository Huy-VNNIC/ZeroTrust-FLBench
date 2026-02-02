#!/usr/bin/env python3
"""
Auto-fill placeholders in manuscript.tex from REPORT.md

Extracts numbers from REPORT.md and replaces placeholders like:
- \P99SEC3NET0{} → 12.3
- \TTASEC0NET0{} → 245.7
- \COMMITHASH{} → abc1234
"""

import argparse
import re
import subprocess
from pathlib import Path


def extract_numbers_from_report(report_path: Path) -> dict:
    """Parse REPORT.md and extract key metrics"""
    
    with open(report_path, 'r') as f:
        content = f.read()
    
    numbers = {}
    
    # Extract overhead percentages from "Key Finding 1"
    # Pattern: "**SEC3 vs SEC0:** +35.2% p99 latency increase"
    overhead_pattern = r'\*\*SEC(\d+) vs SEC0:\*\* \+?([\d.]+)%'
    for match in re.finditer(overhead_pattern, content):
        sec_level = match.group(1)
        overhead = float(match.group(2))
        if sec_level == '3':
            numbers['OVERHEADSEC3'] = f"{overhead:.1f}"
    
    # Extract TTA values from "Key Finding 2"
    # Pattern: "NET2 increases TTA by 42.3% vs NET0"
    tta_pattern = r'NET2 increases TTA by ([\d.]+)%'
    for match in re.finditer(tta_pattern, content):
        tta_increase = float(match.group(1))
        # Store for later use (would need baseline value from summary.csv)
    
    # Extract failure rates from "Key Finding 3"
    # Pattern: "**Highest failure rate:** SEC3/NET2 (4.25%)"
    failure_pattern = r'\*\*Highest failure rate:\*\* SEC(\d+)/NET(\d+) \(([\d.]+)%\)'
    match = re.search(failure_pattern, content)
    if match:
        failure_rate = float(match.group(3))
        numbers['FAILSEC3NET2'] = f"{failure_rate:.2f}"
    
    # Extract p-value and effect size
    pvalue_pattern = r'p-value: ([\d.]+)'
    match = re.search(pvalue_pattern, content)
    if match:
        numbers['PVALUE_SEC0_SEC3'] = f"{float(match.group(1)):.4f}"
    
    return numbers


def extract_from_summary_csv(summary_csv_path: Path) -> dict:
    """Extract specific metrics from summary.csv"""
    
    import pandas as pd
    
    df = pd.read_csv(summary_csv_path)
    numbers = {}
    
    # SEC0/NET0 baseline
    baseline = df[(df['sec_level'] == 'SEC0') & (df['net_profile'] == 'NET0')]
    if len(baseline) > 0:
        numbers['P99SEC0NET0'] = f"{baseline['p99_round'].mean():.1f}"
        if 'tta_95' in baseline.columns:
            tta = baseline['tta_95'].mean()
            if pd.notna(tta):
                numbers['TTASEC0NET0'] = f"{tta:.1f}"
    
    # SEC3/NET0
    sec3_net0 = df[(df['sec_level'] == 'SEC3') & (df['net_profile'] == 'NET0')]
    if len(sec3_net0) > 0:
        numbers['P99SEC3NET0'] = f"{sec3_net0['p99_round'].mean():.1f}"
        if 'tta_95' in sec3_net0.columns:
            tta = sec3_net0['tta_95'].mean()
            if pd.notna(tta):
                numbers['TTASEC3NET0'] = f"{tta:.1f}"
    
    # SEC3/NET2
    sec3_net2 = df[(df['sec_level'] == 'SEC3') & (df['net_profile'] == 'NET2')]
    if len(sec3_net2) > 0:
        numbers['P99SEC3NET2'] = f"{sec3_net2['p99_round'].mean():.1f}"
        if 'tta_95' in sec3_net2.columns:
            tta = sec3_net2['tta_95'].mean()
            if pd.notna(tta):
                numbers['TTASEC3NET2'] = f"{tta:.1f}"
        numbers['FAILSEC3NET2'] = f"{sec3_net2['failure_rate'].mean() * 100:.2f}"
    
    # Calculate overhead
    if 'P99SEC0NET0' in numbers and 'P99SEC3NET0' in numbers:
        baseline_p99 = float(numbers['P99SEC0NET0'])
        sec3_p99 = float(numbers['P99SEC3NET0'])
        overhead = ((sec3_p99 - baseline_p99) / baseline_p99) * 100
        numbers['OVERHEADSEC3'] = f"{overhead:.1f}"
    
    return numbers


def get_git_commit() -> str:
    """Get current git commit hash"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False
        )
        return result.stdout.strip() or "unknown"
    except:
        return "unknown"


def fill_placeholders(template_path: Path, numbers: dict, output_path: Path):
    """Replace placeholders in LaTeX template"""
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Add git commit
    numbers['COMMITHASH'] = get_git_commit()
    
    # Replace each placeholder
    for key, value in numbers.items():
        # Pattern: \KEYNAME{} or \KEYNAME
        pattern = rf'\\{key}\{{\}}'
        content = re.sub(pattern, value, content)
        
        # Also try without braces
        pattern = rf'\[{key}\]'
        content = re.sub(pattern, value, content)
    
    # Write output
    with open(output_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Filled {len(numbers)} placeholders")
    print(f"   Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Auto-fill manuscript placeholders")
    parser.add_argument("--template", type=Path, default=Path("paper/manuscript.tex"))
    parser.add_argument("--report", type=Path, default=Path("paper/REPORT.md"))
    parser.add_argument("--summary-csv", type=Path, default=Path("results/processed/summary.csv"))
    parser.add_argument("--output", type=Path, default=Path("paper/manuscript_filled.tex"))
    
    args = parser.parse_args()
    
    print("📝 Auto-filling manuscript placeholders...")
    print("")
    
    # Extract numbers
    numbers = {}
    
    if args.report.exists():
        print(f"📊 Extracting from REPORT.md...")
        report_numbers = extract_numbers_from_report(args.report)
        numbers.update(report_numbers)
        print(f"   Found {len(report_numbers)} values")
    
    if args.summary_csv.exists():
        print(f"📊 Extracting from summary.csv...")
        csv_numbers = extract_from_summary_csv(args.summary_csv)
        numbers.update(csv_numbers)
        print(f"   Found {len(csv_numbers)} values")
    
    print("")
    print("📋 Extracted values:")
    for key, value in sorted(numbers.items()):
        print(f"   {key:20s} = {value}")
    
    print("")
    
    # Fill template
    fill_placeholders(args.template, numbers, args.output)
    
    print("")
    print("✅ DONE!")
    print(f"   Compile: cd paper && pdflatex {args.output.name}")


if __name__ == "__main__":
    main()
