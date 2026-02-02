#!/usr/bin/env python3
"""
Experiment Matrix Runner for ZeroTrust-FLBench

Automatically runs the full experiment matrix with proper cleanup between runs.
"""

import argparse
import itertools
import json
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
    
    # Wait for deletion
    time.sleep(20)
    
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


def apply_network_profile(profile):
    """Apply network emulation profile"""
    if profile == "NET0":
        print(f"📡 Network profile: {profile} (no impairment)")
        return
    
    print(f"📡 Applying network profile: {profile}")
    result = subprocess.run(
        ["bash", "scripts/netem_apply.sh", profile],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Failed to apply network profile: {result.stderr}")
        return False
    
    print(result.stdout)
    return True


def apply_security_config(sec_config):
    """Apply security configuration"""
    print(f"🔒 Applying security config: {sec_config}")
    
    k8s_path = Path(__file__).parent.parent / "k8s"
    
    if sec_config == "SEC0":
        # Baseline only
        manifest_path = k8s_path / "00-baseline" / "fl-deployment.yaml"
    elif sec_config == "SEC1":
        # Baseline + NetworkPolicy
        manifest_path = k8s_path / "00-baseline" / "fl-deployment.yaml"
        policy_path = k8s_path / "10-networkpolicy" / "networkpolicies.yaml"
        
        subprocess.run(["kubectl", "apply", "-f", str(manifest_path)])
        subprocess.run(["kubectl", "apply", "-f", str(policy_path)])
        return True
    elif sec_config == "SEC2":
        # Baseline + mTLS (requires Linkerd installed)
        print("⚠️  SEC2 (mTLS) requires Linkerd to be pre-installed")
        print("    Run: linkerd install | kubectl apply -f -")
        manifest_path = k8s_path / "00-baseline" / "fl-deployment.yaml"
        # TODO: Add Linkerd injection annotation
    elif sec_config == "SEC3":
        # NetworkPolicy + mTLS
        print("⚠️  SEC3 requires Linkerd to be pre-installed")
        manifest_path = k8s_path / "00-baseline" / "fl-deployment.yaml"
        policy_path = k8s_path / "10-networkpolicy" / "networkpolicies.yaml"
        
        subprocess.run(["kubectl", "apply", "-f", str(manifest_path)])
        subprocess.run(["kubectl", "apply", "-f", str(policy_path)])
        return True
    
    result = subprocess.run(
        ["kubectl", "apply", "-f", str(manifest_path)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Failed to apply manifest: {result.stderr}")
        return False
    
    return True


def wait_for_pods_ready(namespace="fl-experiment", timeout=300):
    """Wait for all pods to be ready"""
    print("⏳ Waiting for pods to be ready...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        
        # Check if server is running
        if "fl-server" in result.stdout and "Running" in result.stdout:
            # Check if clients are running or completed
            client_lines = [l for l in result.stdout.split('\n') if 'fl-client' in l]
            if len(client_lines) >= 5:  # At least 5 clients
                print("✅ Pods ready")
                return True
        
        time.sleep(10)
    
    print("❌ Timeout waiting for pods")
    return False


def collect_logs(run_id, results_dir):
    """Collect logs from FL server and clients"""
    print("📝 Collecting logs...")
    
    run_dir = results_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Server logs
    result = subprocess.run(
        ["kubectl", "logs", "-n", "fl-experiment", "deployment/fl-server"],
        capture_output=True,
        text=True
    )
    
    with open(run_dir / "server.log", "w") as f:
        f.write(result.stdout)
    
    # Client logs
    client_logs = []
    for i in range(5):  # Assume 5 clients
        result = subprocess.run(
            ["kubectl", "logs", "-n", "fl-experiment", f"job/fl-client-{i}"],
            capture_output=True,
            text=True
        )
        client_logs.append(result.stdout)
    
    with open(run_dir / "clients.log", "w") as f:
        f.write("\n".join(client_logs))
    
    print(f"✅ Logs saved to {run_dir}")


def save_metadata(run_id, config, results_dir):
    """Save run metadata"""
    run_dir = results_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    metadata = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "config": config,
        "environment": {
            "k8s_version": subprocess.run(
                ["kubectl", "version", "--short"],
                capture_output=True,
                text=True
            ).stdout.strip()
        }
    }
    
    with open(run_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)


def run_single_experiment(workload, data_dist, num_clients, net_profile, sec_config, seed, results_dir):
    """Run a single experiment configuration"""
    
    run_id = generate_run_id(workload, data_dist, num_clients, net_profile, sec_config, seed)
    
    print("\n" + "="*80)
    print(f"🚀 Starting run: {run_id}")
    print("="*80)
    
    config = {
        "workload": workload,
        "data_distribution": data_dist,
        "num_clients": num_clients,
        "network_profile": net_profile,
        "security_config": sec_config,
        "seed": seed
    }
    
    # Save metadata first
    save_metadata(run_id, config, results_dir)
    
    # Step 1: Cleanup
    cleanup_namespace()
    
    # Step 2: Reset network
    reset_network()
    
    # Step 3: Apply network profile
    if not apply_network_profile(net_profile):
        print(f"❌ Failed run: {run_id}")
        return False
    
    # Step 4: Apply security config
    if not apply_security_config(sec_config):
        print(f"❌ Failed run: {run_id}")
        return False
    
    # Step 5: Wait for pods
    if not wait_for_pods_ready():
        print(f"❌ Failed run: {run_id}")
        collect_logs(run_id, results_dir)  # Collect logs anyway for debugging
        return False
    
    # Step 6: Wait for training to complete
    # Monitor server logs for "experiment_end" event
    print("⏳ Waiting for training to complete...")
    
    max_training_time = 1800  # 30 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_training_time:
        result = subprocess.run(
            ["kubectl", "logs", "-n", "fl-experiment", "deployment/fl-server", "--tail=50"],
            capture_output=True,
            text=True
        )
        
        if "experiment_end" in result.stdout:
            print("✅ Training completed")
            break
        
        time.sleep(30)
    else:
        print("⚠️  Training timeout (may still be running)")
    
    # Step 7: Collect logs
    collect_logs(run_id, results_dir)
    
    # Step 8: Cool-down
    print("⏳ Cool-down period...")
    time.sleep(60)
    
    print(f"✅ Completed run: {run_id}\n")
    return True


def generate_experiment_list(tier="core"):
    """Generate list of experiment configurations"""
    
    if tier == "core":
        # Tier 1: Core set (80 runs)
        configs = list(itertools.product(
            ['mnist'],           # workload
            DATA_DISTRIBUTIONS,  # iid, noniid
            [5],                 # num_clients
            ['NET0', 'NET2'],    # networks
            SECURITY_CONFIGS,    # SEC0-SEC3
            SEEDS                # 5 seeds
        ))
    elif tier == "extended":
        # Tier 2: Extended set (320 runs total)
        configs = list(itertools.product(
            ['mnist'],
            DATA_DISTRIBUTIONS,
            NUM_CLIENTS_LIST,    # 5, 10
            NETWORK_PROFILES,    # NET0, NET2, NET4
            SECURITY_CONFIGS,
            SEEDS
        ))
    elif tier == "full":
        # Tier 3: Full set (480 runs)
        configs = list(itertools.product(
            ['mnist', 'cifar10'],
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
            
            # Ask if should continue on failure
            response = input("❓ Continue despite failure? (y/n): ")
            if response.lower() != 'y':
                print("🛑 Stopping experiment run")
                break
    
    print("\n" + "="*80)
    print("🏁 Experiment run complete")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print("="*80)


if __name__ == "__main__":
    main()
