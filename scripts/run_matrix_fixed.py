#!/usr/bin/env python3
"""
Experiment Matrix Runner for ZeroTrust-FLBench (FIXED VERSION)

Automatically runs the full experiment matrix by calling run_one.py for each configuration.
"""

import argparse
import itertools
import subprocess
import time
from pathlib import Path
from datetime import datetime
import sys


# Experiment matrix dimensions
WORKLOADS = {
    'mnist': {
        'model': 'cnn',
        'num_rounds': 50,
        'target_acc': [95.0, 97.0]
    },
    'cifar10': {
        'model': 'cnn',
        'num_rounds': 100,
        'target_acc': [60.0, 70.0]
    }
}

DATA_DISTRIBUTIONS = ['iid', 'noniid']
NUM_CLIENTS_LIST = [5, 10]
NETWORK_PROFILES = ['NET0', 'NET2', 'NET4']
SECURITY_CONFIGS = ['SEC0', 'SEC1', 'SEC2', 'SEC3']
SEEDS = [0, 1, 2, 3, 4]


def generate_run_id(workload, data_dist, num_clients, net_profile, sec_config, seed):
    """Generate unique run ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{workload}_{data_dist}_{num_clients}c_{net_profile}_{sec_config}_seed{seed}"


def wait_for_cluster_ready():
    """Wait for cluster to be in clean state"""
    print("⏳ Waiting for cluster stabilization...")
    time.sleep(10)
    
    # Check node status
    result = subprocess.run(
        ["kubectl", "get", "nodes"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    
    if result.returncode != 0:
        print("❌ Cluster not ready")
        return False
    
    return True


def cleanup_namespace():
    """Clean up experiment namespace"""
    print("🧹 Cleaning up namespace...")
    
    # Delete namespace (this removes all resources)
    subprocess.run(
        ["kubectl", "delete", "namespace", "fl-experiment", "--ignore-not-found=true"],
        capture_output=True
    )
    
    # Wait for namespace to fully terminate (can take 30-60s)
    print("⏳ Waiting for namespace termination...")
    max_wait = 120  # 2 minutes max
    start = time.time()
    while time.time() - start < max_wait:
        result = subprocess.run(
            ["kubectl", "get", "namespace", "fl-experiment"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:  # Namespace doesn't exist anymore
            break
        time.sleep(5)
    
    # Extra buffer to ensure everything is cleaned
    time.sleep(10)
    
    # Recreate namespace
    subprocess.run(
        ["kubectl", "create", "namespace", "fl-experiment"],
        capture_output=True
    )
    
    print("✅ Namespace cleaned")


def reset_network():
    """Reset network emulation"""
    print("🔄 Resetting network...")
    subprocess.run(
        ["bash", "scripts/netem_reset.sh"],
        cwd=Path(__file__).parent.parent
    )


def run_single_experiment(workload, data_dist, num_clients, net_profile, sec_config, seed, results_dir):
    """Run a single experiment configuration by calling run_one.py"""
    
    run_id = generate_run_id(workload, data_dist, num_clients, net_profile, sec_config, seed)
    
    print("\n" + "="*80)
    print(f"🚀 Starting run: {run_id}")
    print(f"   Config: {workload} {data_dist} {num_clients}c {net_profile} {sec_config} seed={seed}")
    print("="*80)
    
    # Step 1: Cleanup
    cleanup_namespace()
    
    # Step 2: Reset network
    reset_network()
    
    # Step 3: Run experiment using run_one.py
    script_dir = Path(__file__).parent
    num_rounds = WORKLOADS[workload]['num_rounds']
    
    cmd = [
        "python3",
        str(script_dir / "run_one.py"),
        "--sec-level", sec_config,
        "--net-profile", net_profile,
        "--num-clients", str(num_clients),
        "--num-rounds", str(num_rounds),
        "--data-seed", str(seed)
    ]
    
    # Add IID/non-IID flag
    if data_dist == "iid":
        cmd.append("--iid")
    
    print(f"🔧 Command: {' '.join(cmd)}")
    
    result = subprocess.run(
        cmd,
        cwd=script_dir.parent
    )
    
    if result.returncode != 0:
        print(f"❌ Failed run: {run_id}")
        return False
    
    print(f"✅ Completed run: {run_id}\n")
    return True


def generate_experiment_list(tier="core"):
    """Generate list of experiment configurations"""
    
    if tier == "core":
        # Tier 1: Core set (80 runs)
        # mnist × [iid, noniid] × 5 clients × [NET0, NET2] × [SEC0-SEC3] × 5 seeds
        configs = list(itertools.product(
            ['mnist'],           # workload
            DATA_DISTRIBUTIONS,  # iid, noniid
            [5],                 # num_clients
            ['NET0', 'NET2'],    # network_profiles
            SECURITY_CONFIGS,    # SEC0-SEC3
            SEEDS                # seeds 0-4
        ))
    elif tier == "extended":
        # Tier 2: Extended set (320 runs)
        # Add 10 clients and NET4
        configs = list(itertools.product(
            ['mnist'],
            DATA_DISTRIBUTIONS,
            NUM_CLIENTS_LIST,
            NETWORK_PROFILES,
            SECURITY_CONFIGS,
            SEEDS
        ))
    elif tier == "full":
        # Tier 3: Full set (480 runs)
        # Add CIFAR-10
        configs = list(itertools.product(
            WORKLOADS.keys(),
            DATA_DISTRIBUTIONS,
            NUM_CLIENTS_LIST,
            NETWORK_PROFILES,
            SECURITY_CONFIGS,
            SEEDS
        ))
    else:
        raise ValueError(f"Unknown tier: {tier}")
    
    return configs


def main():
    parser = argparse.ArgumentParser(description="Run ZeroTrust-FLBench experiments")
    parser.add_argument(
        "--tier",
        choices=["core", "extended", "full"],
        default="core",
        help="Experiment tier to run"
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path(__file__).parent.parent / "results" / "raw",
        help="Directory to save results"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print experiment list without running"
    )
    parser.add_argument(
        "--resume-from",
        type=int,
        default=0,
        help="Resume from experiment number (0-indexed)"
    )
    
    args = parser.parse_args()
    
    # Create results directory
    args.results_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate experiment list
    configs = generate_experiment_list(args.tier)
    
    print(f"📊 Experiment tier: {args.tier}")
    print(f"📊 Total experiments: {len(configs)}")
    print(f"📁 Results directory: {args.results_dir}")
    
    if args.dry_run:
        print("\n🔍 Dry run - experiment list:")
        for i, config in enumerate(configs):
            print(f"  {i}: {config}")
        sys.exit(0)
    
    # Check cluster readiness
    if not wait_for_cluster_ready():
        print("❌ Cluster not ready. Exiting.")
        sys.exit(1)
    
    # Run experiments
    success_count = 0
    fail_count = 0
    
    for i, config in enumerate(configs):
        if i < args.resume_from:
            print(f"⏭️  Skipping experiment {i} (resume point)")
            continue
        
        print(f"\n📊 Experiment {i+1}/{len(configs)}")
        
        success = run_single_experiment(
            workload=config[0],
            data_dist=config[1],
            num_clients=config[2],
            net_profile=config[3],
            sec_config=config[4],
            seed=config[5],
            results_dir=args.results_dir
        )
        
        if success:
            success_count += 1
        else:
            fail_count += 1
            print("⚠️  Continuing despite failure (auto-continue enabled)")
            # Continue automatically - no user input needed
    
    print("\n" + "="*80)
    print("🏁 Experiment run complete")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print("="*80)


if __name__ == "__main__":
    main()
