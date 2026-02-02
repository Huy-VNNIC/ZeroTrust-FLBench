#!/usr/bin/env python3
"""
Real-time monitoring of ZeroTrust FL experiment matrix
Tracks progress, success rate, and generates live reports
"""

import time
import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import subprocess
import psutil
from datetime import datetime, timedelta
import argparse

def get_matrix_processes():
    """Get currently running matrix processes"""
    processes = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            if 'python3' in cmdline and 'run_matrix' in cmdline:
                processes.append({
                    'pid': proc.info['pid'],
                    'cmdline': cmdline,
                    'runtime': time.time() - proc.info['create_time'],
                    'status': proc.status()
                })
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    
    return processes

def count_experiments():
    """Count completed experiments"""
    results_dir = Path("results/raw")
    completed = len(list(results_dir.glob("202*")))
    return completed

def get_latest_log():
    """Get the most recent matrix log file"""
    log_files = [
        "results/matrix_run_FIXED.log",
        "results/matrix_run_fixed.log", 
        "results/matrix_run_FINAL.log",
        "results/matrix_run_final.log",
        "results/matrix_run.log"
    ]
    
    latest_log = None
    latest_time = 0
    
    for log_file in log_files:
        log_path = Path(log_file)
        if log_path.exists():
            mtime = log_path.stat().st_mtime
            if mtime > latest_time:
                latest_time = mtime
                latest_log = log_path
                
    return latest_log

def parse_log_progress(log_file, tail_lines=50):
    """Parse progress from log file"""
    if not log_file or not log_file.exists():
        return {}
    
    try:
        # Get last N lines efficiently
        result = subprocess.run(
            ['tail', '-n', str(tail_lines), str(log_file)],
            capture_output=True, text=True, timeout=5
        )
        
        lines = result.stdout.split('\n')
        
        # Find experiment progress
        current_exp = None
        total_exp = None
        status = "unknown"
        
        for line in reversed(lines):
            if "Experiment " in line and "/" in line:
                # Extract "Experiment X/Y"
                import re
                match = re.search(r'Experiment (\d+)/(\d+)', line)
                if match:
                    current_exp = int(match.group(1))
                    total_exp = int(match.group(2))
                    break
                    
        # Check for failure/success indicators
        for line in reversed(lines[-10:]):  # Last 10 lines
            if "✅" in line or "SUCCESS" in line:
                status = "success"
                break
            elif "❌" in line or "FAILED" in line or "ERROR" in line:
                status = "failed"
                break
            elif "🚀" in line or "Starting" in line:
                status = "running"
                break
                
        return {
            'current_experiment': current_exp,
            'total_experiments': total_exp,
            'status': status,
            'log_file': str(log_file)
        }
        
    except Exception as e:
        return {'error': str(e)}

def generate_live_report():
    """Generate live monitoring report"""
    
    print("🔄 ZeroTrust FL Matrix - Live Monitoring Report")
    print("=" * 60)
    print(f"⏰ Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check processes
    processes = get_matrix_processes()
    print(f"\n🔍 Active Matrix Processes: {len(processes)}")
    
    for i, proc in enumerate(processes, 1):
        runtime_hours = proc['runtime'] / 3600
        print(f"  {i}. PID {proc['pid']}: {runtime_hours:.1f}h runtime ({proc['status']})")
        print(f"     {proc['cmdline'][:80]}...")
    
    # Check completed experiments
    completed = count_experiments()
    print(f"\n📊 Completed Experiments: {completed}")
    print(f"📈 Progress: {completed}/80 ({completed/80*100:.1f}%)")
    
    # Check log progress
    latest_log = get_latest_log()
    if latest_log:
        progress = parse_log_progress(latest_log)
        print(f"\n📄 Latest Log: {latest_log.name}")
        
        if 'current_experiment' in progress and progress['current_experiment']:
            print(f"🎯 Current Progress: {progress['current_experiment']}/{progress['total_experiments']}")
            print(f"📊 Log Progress: {progress['current_experiment']/progress['total_experiments']*100:.1f}%")
        
        print(f"🔹 Status: {progress.get('status', 'unknown')}")
    
    # Success rate analysis
    if completed > 0:
        print(f"\n✅ SUCCESS RATE SUMMARY:")
        try:
            # Quick analysis using our existing script
            import sys
            sys.path.append('scripts')
            from analyze_results import analyze_experiments
            
            df = analyze_experiments()
            if len(df) > 0:
                net_counts = df['network'].value_counts()
                sec_counts = df['security'].value_counts()
                
                print(f"📡 Network Profiles:")
                for net, count in net_counts.items():
                    print(f"   {net}: {count} experiments")
                    
                print(f"🔒 Security Levels:")  
                for sec, count in sec_counts.items():
                    print(f"   {sec}: {count} experiments")
                    
        except Exception as e:
            print(f"   ⚠️ Could not analyze: {e}")
    
    # Estimated completion
    if processes and completed > 0:
        avg_runtime = sum(p['runtime'] for p in processes) / len(processes)
        if avg_runtime > 0:
            estimated_total_time = (80 / completed) * avg_runtime
            remaining_time = estimated_total_time - avg_runtime
            
            print(f"\n⏳ ESTIMATED COMPLETION:")
            print(f"   Average Runtime: {avg_runtime/3600:.1f}h per experiment")
            print(f"   Estimated Total: {estimated_total_time/3600:.1f}h")
            print(f"   Remaining Time: {remaining_time/3600:.1f}h")
            print(f"   Estimated Finish: {(datetime.now() + timedelta(seconds=remaining_time)).strftime('%H:%M')}")

def continuous_monitor(interval=60):
    """Continuous monitoring with specified interval"""
    
    print(f"🚀 Starting continuous monitoring (refresh every {interval}s)")
    print("Press Ctrl+C to stop...")
    
    try:
        while True:
            # Clear screen (Unix systems)
            subprocess.run(['clear'])
            
            generate_live_report()
            
            print(f"\n{'='*60}")
            print(f"⏱️  Next update in {interval} seconds... (Ctrl+C to stop)")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped by user")
        
def save_monitoring_log():
    """Save monitoring snapshot to file"""
    
    log_file = Path("results/monitoring_log.txt")
    
    with open(log_file, 'a') as f:
        f.write(f"\n=== MONITORING LOG {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        
        # Processes
        processes = get_matrix_processes()
        f.write(f"Active Processes: {len(processes)}\n")
        for proc in processes:
            f.write(f"  PID {proc['pid']}: {proc['runtime']/3600:.1f}h\n")
        
        # Completed experiments
        completed = count_experiments()
        f.write(f"Completed: {completed}/80 ({completed/80*100:.1f}%)\n")
        
        # Log status
        latest_log = get_latest_log()
        if latest_log:
            progress = parse_log_progress(latest_log)
            f.write(f"Log Progress: {progress.get('current_experiment', '?')}/{progress.get('total_experiments', '?')}\n")
            f.write(f"Status: {progress.get('status', 'unknown')}\n")
        
        f.write("\n")
    
    print(f"📝 Monitoring snapshot saved to {log_file}")

def main():
    parser = argparse.ArgumentParser(description="Monitor ZeroTrust FL experiment matrix")
    parser.add_argument('--continuous', '-c', action='store_true', 
                       help='Run continuous monitoring')
    parser.add_argument('--interval', '-i', type=int, default=60,
                       help='Update interval in seconds (default: 60)')
    parser.add_argument('--save-log', '-s', action='store_true',
                       help='Save monitoring snapshot to file')
    
    args = parser.parse_args()
    
    if args.save_log:
        save_monitoring_log()
    elif args.continuous:
        continuous_monitor(args.interval)
    else:
        generate_live_report()

if __name__ == "__main__":
    main()