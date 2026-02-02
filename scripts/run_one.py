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


def apply_network_profile(profile: str, namespace: str):
    """Apply tc/netem network emulation profile"""
    if profile == "NET0":
        # No network constraints (baseline)
        log_event("network_profile_skip", profile=profile, reason="baseline")
        return
    
    # Get all client pods
    result = run_command([
        "kubectl", "get", "pods",
        "-n", namespace,
        "-l", "app=fl-client",
        "-o", "jsonpath={.items[*].metadata.name}"
    ])
    
    pods = result.stdout.strip().split()
    
    if not pods:
        log_event("network_profile_skip", profile=profile, reason="no_pods")
        return
    
    # Apply netem rules based on profile
    netem_script = Path(__file__).parent / "netem_apply.sh"
    
    for pod in pods:
        log_event("network_profile_apply", profile=profile, pod=pod, namespace=namespace)
        run_command([
            str(netem_script),
            namespace,
            pod,
            profile
        ])


def inject_run_id(manifest_path: Path, run_id: str, output_path: Path):
    """Replace PLACEHOLDER with actual RUN_ID in manifest"""
    with open(manifest_path) as f:
        content = f.read()
    
    # Replace all PLACEHOLDER occurrences with actual RUN_ID
    content = content.replace('run-id: "PLACEHOLDER"', f'run-id: "{run_id}"')
    
    with open(output_path, 'w') as f:
        f.write(content)
    
    log_event(
        "manifest_prepared",
        source=str(manifest_path),
        output=str(output_path),
        run_id=run_id
    )


def wait_for_server_ready(namespace: str, timeout: int = 300):
    """Wait for FL server pod to be Running"""
    log_event("wait_server_start", namespace=namespace, timeout_sec=timeout)
    start = time.time()
    
    while time.time() - start < timeout:
        result = run_command([
            "kubectl", "get", "pods",
            "-n", namespace,
            "-l", "app=fl-server",
            "-o", "jsonpath={.items[0].status.phase}"
        ], check=False)
        
        phase = result.stdout.strip()
        if phase == "Running":
            log_event("wait_server_ready", namespace=namespace, duration_sec=time.time() - start)
            return True
        
        time.sleep(2)
    
    log_event("wait_server_timeout", namespace=namespace, timeout_sec=timeout)
    return False


def wait_for_completion(namespace: str, timeout: int = 3600):
    """Wait for all client jobs to complete"""
    log_event("wait_completion_start", namespace=namespace, timeout_sec=timeout)
    start = time.time()
    
    while time.time() - start < timeout:
        # Check all client jobs
        result = run_command([
            "kubectl", "get", "jobs",
            "-n", namespace,
            "-l", "app=fl-client",
            "-o", "json"
        ])
        
        jobs_data = json.loads(result.stdout)
        
        if not jobs_data.get("items"):
            log_event("wait_completion_no_jobs", namespace=namespace)
            return False
        
        all_complete = True
        failed = False
        
        for job in jobs_data["items"]:
            status = job.get("status", {})
            succeeded = status.get("succeeded", 0)
            failed_count = status.get("failed", 0)
            
            if failed_count > 0:
                log_event(
                    "job_failed",
                    job_name=job["metadata"]["name"],
                    failed_count=failed_count
                )
                failed = True
            elif succeeded == 0:
                all_complete = False
        
        if failed:
            log_event("wait_completion_failed", namespace=namespace)
            return False
        
        if all_complete:
            duration = time.time() - start
            log_event("wait_completion_success", namespace=namespace, duration_sec=duration)
            return True
        
        time.sleep(5)
    
    log_event("wait_completion_timeout", namespace=namespace, timeout_sec=timeout)
    return False


def collect_logs(namespace: str, run_id: str, output_dir: Path):
    """Collect logs from server and all clients"""
    log_event("logs_collect_start", namespace=namespace, run_id=run_id)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Server logs
    log_event("logs_collect_server", namespace=namespace)
    result = run_command([
        "kubectl", "get", "pods",
        "-n", namespace,
        "-l", "app=fl-server",
        "-o", "jsonpath={.items[0].metadata.name}"
    ])
    
    server_pod = result.stdout.strip()
    if server_pod:
        server_log = output_dir / f"server_{run_id}.log"
        with open(server_log, 'w') as f:
            run_command(
                ["kubectl", "logs", "-n", namespace, server_pod],
                check=False
            ).stdout
            subprocess.run(
                ["kubectl", "logs", "-n", namespace, server_pod],
                stdout=f,
                stderr=subprocess.STDOUT,
                check=False
            )
        log_event("logs_collected_server", file=str(server_log))
    
    # Client logs
    result = run_command([
        "kubectl", "get", "pods",
        "-n", namespace,
        "-l", "app=fl-client",
        "-o", "jsonpath={.items[*].metadata.name}"
    ])
    
    client_pods = result.stdout.strip().split()
    for pod in client_pods:
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


def cleanup(namespace: str, keep_namespace: bool = False):
    """Delete resources (optionally keep namespace)"""
    log_event("cleanup_start", namespace=namespace, keep_namespace=keep_namespace)
    
    # Delete all jobs and deployments
    run_command(
        ["kubectl", "delete", "jobs,deployments,services", "-n", namespace, "--all"],
        check=False
    )
    
    if not keep_namespace:
        run_command(["kubectl", "delete", "namespace", namespace], check=False)
    
    log_event("cleanup_end", namespace=namespace)


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
    
    # Generate unique RUN_ID
    run_id = f"{args.sec_level}_{args.net_profile}_{int(time.time())}"
    
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
        
        # Create temporary manifest with RUN_ID injected
        temp_manifest = Path(f"/tmp/fl-deployment-{run_id}.yaml")
        inject_run_id(manifest_path, run_id, temp_manifest)
        
        # Apply manifest
        log_event("apply_manifest", manifest=str(temp_manifest))
        run_command(["kubectl", "apply", "-f", str(temp_manifest)])
        
        # Wait for server to be ready
        if not wait_for_server_ready("fl-experiment", timeout=300):
            log_event("experiment_failed", reason="server_not_ready")
            cleanup("fl-experiment", args.keep_namespace)
            sys.exit(1)
        
        # Apply network profile (after server ready, before clients start training)
        time.sleep(10)  # Let clients spawn
        apply_network_profile(args.net_profile, "fl-experiment")
        
        # Wait for completion
        if not wait_for_completion("fl-experiment", timeout=3600):
            log_event("experiment_failed", reason="completion_timeout")
            collect_logs("fl-experiment", run_id, args.output_dir)
            cleanup("fl-experiment", args.keep_namespace)
            sys.exit(1)
        
        # Collect logs
        collect_logs("fl-experiment", run_id, args.output_dir)
        
        # Cleanup
        cleanup("fl-experiment", args.keep_namespace)
        
        log_event("experiment_success", run_id=run_id)
        
    except Exception as e:
        log_event("experiment_error", error=str(e), run_id=run_id)
        cleanup("fl-experiment", args.keep_namespace)
        sys.exit(1)
    finally:
        # Remove temp manifest
        temp_manifest = Path(f"/tmp/fl-deployment-{run_id}.yaml")
        if temp_manifest.exists():
            temp_manifest.unlink()


if __name__ == "__main__":
    main()
