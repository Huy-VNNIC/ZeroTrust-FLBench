#!/usr/bin/env python3
"""
Run a single FL experiment with specific configurations

This script:
1. Generates unique RUN_ID
2. Creates namespace if needed
3. Applies network profile (netem)
4. Deploys FL server + clients with run-id label injection
5. Waits for completion
6. Collects logs
7. Cleans up resources
"""

import argparse
import subprocess
import time
import json
import yaml
import os
import sys
from datetime import datetime
from pathlib import Path


def log_event(event: str, **kwargs):
    """Log structured JSON event"""
    log_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": event,
        **kwargs
    }
    print(json.dumps(log_data), flush=True)


def run_command(cmd: list, check=True, capture_output=True):
    """Execute shell command and return result"""
    log_event("command_start", command=" ".join(cmd))
    start = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True
        )
        duration = time.time() - start
        log_event(
            "command_end",
            command=" ".join(cmd),
            duration_sec=duration,
            returncode=result.returncode
        )
        return result
    except subprocess.CalledProcessError as e:
        duration = time.time() - start
        log_event(
            "command_failed",
            command=" ".join(cmd),
            duration_sec=duration,
            returncode=e.returncode,
            stderr=e.stderr if capture_output else None
        )
        raise


def wait_pods_ready(namespace: str, label: str, timeout: int = 180) -> bool:
    """Wait for pods to be Ready with kubectl wait"""
    log_event("wait_pods_ready_start", namespace=namespace, label=label, timeout_sec=timeout)
    
    result = run_command([
        "kubectl", "wait",
        "--for=condition=Ready",
        "pod",
        "-n", namespace,
        "-l", label,
        f"--timeout={timeout}s"
    ], check=False)
    
    success = result.returncode == 0
    log_event("wait_pods_ready_end", namespace=namespace, label=label, success=success)
    return success


def apply_network_profile(profile: str, namespace: str, run_id: str):
    """Apply tc/netem network emulation profile to current run client pods only"""
    if profile == "NET0":
        # No network constraints (baseline)
        log_event("network_profile_skip", profile=profile, reason="baseline")
        return
    
    # ✅ Only target pods from current run (avoid old terminating pods)
    selector = f"app=fl-client,run-id={run_id}"
    
    # ✅ Wait until client pods are Ready (critical for kubectl exec)
    log_event("network_profile_wait_ready", profile=profile, selector=selector)
    if not wait_pods_ready(namespace, selector, timeout=180):
        log_event("network_profile_failed", profile=profile, reason="pods_not_ready", selector=selector)
        raise RuntimeError(f"Client pods not Ready for run {run_id} before netem apply")
    
    # Get ready pods for this specific run
    result = run_command([
        "kubectl", "get", "pods",
        "-n", namespace,
        "-l", selector,
        "-o", "jsonpath={.items[*].metadata.name}"
    ], check=False)
    
    pods = result.stdout.strip().split()
    if not pods:
        log_event("network_profile_failed", profile=profile, reason="no_pods_after_ready", selector=selector)
        raise RuntimeError(f"No client pods found for run {run_id}")
    
    log_event("network_profile_apply_start", profile=profile, run_id=run_id, pods=pods)
    
    # Apply netem with retry logic (kubectl exec can be flaky)
    netem_script = Path(__file__).parent / "netem_apply.sh"
    
    for pod in pods:
        success = False
        for attempt in range(1, 6):  # Retry up to 5 times
            log_event("network_profile_apply_try", profile=profile, pod=pod, attempt=attempt)
            result = run_command([
                str(netem_script),
                namespace,
                pod,
                profile
            ], check=False)
            
            if result.returncode == 0:
                success = True
                log_event("network_profile_apply_success", profile=profile, pod=pod, attempt=attempt)
                break
            else:
                log_event("network_profile_apply_retry", profile=profile, pod=pod, attempt=attempt, 
                         returncode=result.returncode, stderr=result.stderr)
                time.sleep(2)  # Brief wait before retry
        
        if not success:
            log_event("network_profile_apply_failed", profile=profile, pod=pod, run_id=run_id)
            raise RuntimeError(f"netem apply failed for pod {pod} after 5 attempts")
    
    log_event("network_profile_apply_complete", profile=profile, run_id=run_id, pod_count=len(pods))


def inject_run_id(manifest_path: Path, run_id: str, output_path: Path, num_rounds: int = None, 
                  num_clients: int = None, is_iid: bool = None, data_seed: int = None):
    """Replace PLACEHOLDER and inject experiment parameters into manifest"""
    with open(manifest_path) as f:
        content = f.read()
    
    # Replace all PLACEHOLDER occurrences with actual RUN_ID
    content = content.replace('run-id: "PLACEHOLDER"', f'run-id: "{run_id}"')
    content = content.replace('PLACEHOLDER', run_id)  # Replace resource names too
    
    # Inject --num-rounds if provided
    if num_rounds is not None:
        content = content.replace('- "--num-rounds=10"', f'- "--num-rounds={num_rounds}"')
    
    # Inject --min-clients if provided
    if num_clients is not None:
        content = content.replace('- "--min-clients=5"', f'- "--min-clients={num_clients}"')
    
    # Add --iid flag in client args if needed (add after data_seed)
    # Server doesn't need this, only clients
    if is_iid is not None and is_iid:
        # For client Jobs, add --iid flag
        content = content.replace(
            f'- "--server-address=fl-server-{run_id}:8080"',
            f'- "--server-address=fl-server-{run_id}:8080"\n          - "--iid"'
        )
    
    # Inject data_seed if provided (for clients)
    if data_seed is not None:
        # Add after server-address for clients
        if '--iid' not in content.replace(f'- "--server-address=fl-server-{run_id}:8080"', ''):
            content = content.replace(
                f'- "--server-address=fl-server-{run_id}:8080"',
                f'- "--server-address=fl-server-{run_id}:8080"\n          - "--data-seed={data_seed}"'
            )
        else:
            content = content.replace(
                '- "--iid"',
                f'- "--iid"\n          - "--data-seed={data_seed}"'
            )
    
    with open(output_path, 'w') as f:
        f.write(content)
    
    log_event(
        "manifest_prepared",
        source=str(manifest_path),
        output=str(output_path),
        run_id=run_id,
        num_rounds=num_rounds,
        num_clients=num_clients,
        is_iid=is_iid,
        data_seed=data_seed
    )


def wait_for_server_ready(namespace: str, run_id: str, timeout: int = 300):
    """Wait for FL server pod to be Running"""
    log_event("wait_server_start", namespace=namespace, run_id=run_id, timeout_sec=timeout)
    start = time.time()
    
    while time.time() - start < timeout:
        result = run_command([
            "kubectl", "get", "pods",
            "-n", namespace,
            "-l", f"run-id={run_id},app=fl-server",
            "-o", "jsonpath={.items[0].status.phase}"
        ], check=False)
        
        phase = result.stdout.strip()
        if phase == "Running":
            log_event("wait_server_ready", namespace=namespace, run_id=run_id, duration_sec=time.time() - start)
            return True
        
        time.sleep(2)
    
    log_event("wait_server_timeout", namespace=namespace, run_id=run_id, timeout_sec=timeout)
    return False


def wait_for_completion(namespace: str, run_id: str, timeout: int = 3600):
    """Wait for experiment completion by monitoring server logs"""
    log_event("wait_completion_start", namespace=namespace, run_id=run_id, timeout_sec=timeout)
    start = time.time()
    
    # Wait for server pod to exist
    time.sleep(5)
    
    while time.time() - start < timeout:
        # Get server pod name
        result = run_command([
            "kubectl", "get", "pods",
            "-n", namespace,
            "-l", f"run-id={run_id},app=fl-server",
            "-o", "jsonpath={.items[0].metadata.name}"
        ], check=False)
        
        if result.returncode != 0 or not result.stdout.strip():
            log_event("wait_server_pod", namespace=namespace, run_id=run_id, status="not_found")
            time.sleep(5)
            continue
        
        server_pod = result.stdout.strip()
        
        # Check server logs for experiment_end event
        result = run_command([
            "kubectl", "logs",
            "-n", namespace,
            server_pod
        ], check=False)
        
        if result.returncode == 0 and '"event": "experiment_end"' in result.stdout:
            duration = time.time() - start
            log_event("wait_completion_success", namespace=namespace, run_id=run_id, duration_sec=duration)
            return True
        
        # Check if pod failed
        result = run_command([
            "kubectl", "get", "pod",
            "-n", namespace,
            server_pod,
            "-o", "jsonpath={.status.phase}"
        ], check=False)
        
        if result.returncode == 0:
            phase = result.stdout.strip()
            if phase in ["Failed", "Error", "Unknown"]:
                log_event("wait_completion_failed", namespace=namespace, run_id=run_id, pod_phase=phase)
                return False
        
        time.sleep(10)
    
    log_event("wait_completion_timeout", namespace=namespace, run_id=run_id, timeout_sec=timeout)
    return False


def collect_logs(namespace: str, run_id: str, output_dir: Path):
    """Collect logs from server and all clients for this specific run"""
    log_event("logs_collect_start", namespace=namespace, run_id=run_id)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Server logs (filter by run-id)
    log_event("logs_collect_server", namespace=namespace)
    result = run_command([
        "kubectl", "get", "pods",
        "-n", namespace,
        "-l", f"run-id={run_id},app=fl-server",
        "-o", "jsonpath={.items[0].metadata.name}"
    ], check=False)
    
    server_pod = result.stdout.strip()
    if server_pod:
        server_log = output_dir / f"server_{run_id}.log"
        with open(server_log, 'w') as f:
            subprocess.run(
                ["kubectl", "logs", "-n", namespace, server_pod],
                stdout=f,
                stderr=subprocess.STDOUT,
                check=False
            )
        log_event("logs_collected_server", file=str(server_log))
    
    # Client logs (filter by run-id)
    result = run_command([
        "kubectl", "get", "pods",
        "-n", namespace,
        "-l", f"run-id={run_id},app=fl-client",
        "-o", "jsonpath={.items[*].metadata.name}"
    ], check=False)
    
    client_pods = result.stdout.strip().split()
    for pod in client_pods:
        if not pod:  # Skip empty strings
            continue
        client_log = output_dir / f"{pod}_{run_id}.log"
        with open(client_log, 'w') as f:
            subprocess.run(
                ["kubectl", "logs", "-n", namespace, pod],
                stdout=f,
                stderr=subprocess.STDOUT,
                check=False
            )
        log_event("logs_collected_client", pod=pod, file=str(client_log))
    
    log_event("logs_collect_end", namespace=namespace, output_dir=str(output_dir))


def save_metadata(output_dir: Path, run_id: str, config: dict):
    """Save run metadata to meta.json"""
    import subprocess
    
    # Get git commit hash
    try:
        commit_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False
        ).stdout.strip()
    except:
        commit_hash = "unknown"
    
    # Get versions
    metadata = {
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "config": config,
        "versions": {
            "git_commit": commit_hash,
            "python": sys.version,
            "flwr": "1.7.0",  # From requirements.txt
            "torch": "2.1.0",
            "kubernetes": "minikube"
        },
        "environment": {
            "os": os.uname().sysname if hasattr(os, 'uname') else "unknown",
            "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown"
        }
    }
    
    meta_file = output_dir / "meta.json"
    with open(meta_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    log_event("metadata_saved", file=str(meta_file))


def cleanup(namespace: str, run_id: str):
    """Delete resources for this specific run (by run-id), keep namespace"""
    log_event("cleanup_start", namespace=namespace, run_id=run_id)
    
    # Delete only resources with this run-id
    run_command(
        ["kubectl", "delete", "jobs,deployments,services", 
         "-n", namespace, "-l", f"run-id={run_id}"],
        check=False
    )
    
    # Wait for pods to fully terminate
    import time
    max_wait = 60
    start = time.time()
    while time.time() - start < max_wait:
        result = run_command(
            ["kubectl", "get", "pods", "-n", namespace, 
             "-l", f"run-id={run_id}",
             "-o", "jsonpath={.items[*].metadata.name}"],
            check=False
        )
        if not result.stdout.strip():
            break
        time.sleep(3)
    
    log_event("cleanup_end", namespace=namespace, run_id=run_id)


def collect_debug_info(namespace: str, run_id: str, output_dir: Path):
    """Collect debug info when experiment fails"""
    debug_file = output_dir / "debug.txt"
    
    try:
        with open(debug_file, 'w') as f:
            f.write(f"=== DEBUG INFO FOR {run_id} ===\n\n")
            
            # Pod status
            f.write("=== POD STATUS ===\n")
            result = run_command(["kubectl", "get", "pods", "-n", namespace, "-o", "wide"], check=False)
            f.write(result.stdout + "\n\n")
            
            # Jobs status  
            f.write("=== JOBS STATUS ===\n")
            result = run_command(["kubectl", "get", "jobs", "-n", namespace, "-o", "yaml"], check=False)
            f.write(result.stdout[:2000] + "\n\n")  # Limit output
            
            # Recent events
            f.write("=== RECENT EVENTS ===\n")
            result = run_command([
                "kubectl", "get", "events", "-n", namespace, 
                "--sort-by=.lastTimestamp"
            ], check=False)
            lines = result.stdout.split('\n')
            f.write('\n'.join(lines[-30:]) + "\n")  # Last 30 events
        
        log_event("debug_collected", file=str(debug_file))
    except Exception as e:
        log_event("debug_collection_failed", error=str(e))



def main():
    parser = argparse.ArgumentParser(
        description="Run single FL experiment"
    )
    parser.add_argument(
        "--sec-level",
        required=True,
        choices=["SEC0", "SEC1", "SEC2", "SEC3"],
        help="Security configuration"
    )
    parser.add_argument(
        "--net-profile",
        required=True,
        choices=["NET0", "NET1", "NET2", "NET3", "NET4", "NET5"],
        help="Network profile"
    )
    parser.add_argument(
        "--num-clients",
        type=int,
        default=5,
        help="Number of FL clients"
    )
    parser.add_argument(
        "--num-rounds",
        type=int,
        default=10,
        help="Number of FL rounds"
    )
    parser.add_argument(
        "--iid",
        action="store_true",
        default=True,
        help="Use IID data split"
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.5,
        help="Dirichlet alpha for Non-IID"
    )
    parser.add_argument(
        "--data-seed",
        type=int,
        default=42,
        help="Shared data partitioning seed"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/logs"),
        help="Output directory for logs"
    )
    parser.add_argument(
        "--keep-namespace",
        action="store_true",
        help="Keep namespace after completion"
    )
    
    args = parser.parse_args()
    
    # Generate unique RUN_ID (Kubernetes DNS compliant: lowercase, hyphens only)
    run_id = f"{args.sec_level.lower()}-{args.net_profile.lower()}-{int(time.time())}"
    
    log_event(
        "experiment_start",
        run_id=run_id,
        sec_level=args.sec_level,
        net_profile=args.net_profile,
        num_clients=args.num_clients,
        num_rounds=args.num_rounds
    )
    
    try:
        # Determine manifest path based on SEC level
        if args.sec_level == "SEC0":
            manifest_dir = Path("k8s/00-baseline")
        elif args.sec_level == "SEC1":
            manifest_dir = Path("k8s/10-networkpolicy")
        elif args.sec_level == "SEC2":
            manifest_dir = Path("k8s/20-mtls")
        else:  # SEC3
            manifest_dir = Path("k8s/25-combined")
        
        manifest_path = manifest_dir / "fl-deployment.yaml"
        
        if not manifest_path.exists():
            log_event("manifest_not_found", path=str(manifest_path))
            sys.exit(1)
        
        # Create temporary manifest with RUN_ID and parameters injected
        temp_manifest = Path(f"/tmp/fl-deployment-{run_id}.yaml")
        inject_run_id(
            manifest_path, 
            run_id, 
            temp_manifest,
            num_rounds=args.num_rounds,
            num_clients=args.num_clients,
            is_iid=args.iid,
            data_seed=args.data_seed
        )
        
        # Apply manifest
        log_event("apply_manifest", manifest=str(temp_manifest))
        run_command(["kubectl", "apply", "-f", str(temp_manifest)])
        
        # Wait for server to be ready
        if not wait_for_server_ready("fl-experiment", run_id, timeout=300):
            log_event("experiment_failed", reason="server_not_ready")
            cleanup("fl-experiment", run_id)
            sys.exit(1)
        
        # Apply network profile (after server ready, before completion check)
        time.sleep(10)  # Let clients spawn
        apply_network_profile(args.net_profile, "fl-experiment", run_id)
        
        # Wait for completion with dynamic timeout based on network profile
        timeout = 7200 if args.net_profile == "NET2" else 3600  # 2h for NET2, 1h for others
        if not wait_for_completion("fl-experiment", run_id, timeout=timeout):
            log_event("experiment_failed", reason="completion_timeout", timeout_sec=timeout)
            
            # Collect debug info before cleanup
            debug_dir = args.output_dir / run_id
            debug_dir.mkdir(parents=True, exist_ok=True)
            collect_debug_info("fl-experiment", run_id, debug_dir)
            
            collect_logs("fl-experiment", run_id, args.output_dir)
            cleanup("fl-experiment", run_id)
            sys.exit(1)
        
        # Collect logs
        output_dir_run = args.output_dir / run_id
        collect_logs("fl-experiment", run_id, output_dir_run)
        
        # Save metadata
        config_dict = {
            "sec_level": args.sec_level,
            "net_profile": args.net_profile,
            "num_clients": args.num_clients,
            "num_rounds": args.num_rounds,
            "iid": args.iid,
            "alpha": args.alpha,
            "data_seed": args.data_seed
        }
        save_metadata(output_dir_run, run_id, config_dict)
        
        # Cleanup
        cleanup("fl-experiment", run_id)
        
        log_event("experiment_success", run_id=run_id)
        
    except Exception as e:
        log_event("experiment_error", error=str(e), run_id=run_id)
        
        # Collect debug info
        try:
            debug_dir = args.output_dir / run_id
            debug_dir.mkdir(parents=True, exist_ok=True)
            collect_debug_info("fl-experiment", run_id, debug_dir)
        except:
            pass
        
        # Clean up temp file before calling cleanup
        try:
            temp_manifest = Path(f"/tmp/fl-deployment-{run_id}.yaml")
            if temp_manifest.exists():
                temp_manifest.unlink()
        except:
            pass
        cleanup("fl-experiment", run_id)
        sys.exit(1)
    finally:
        # Remove temp manifest (if still exists)
        try:
            temp_manifest = Path(f"/tmp/fl-deployment-{run_id}.yaml")
            if temp_manifest.exists():
                temp_manifest.unlink()
        except:
            pass


if __name__ == "__main__":
    main()
