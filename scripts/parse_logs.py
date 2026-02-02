#!/usr/bin/env python3
"""
Parse FL experiment logs and generate structured CSVs

Generates:
- rounds.csv: Per-round metrics (latency, accuracy, loss)
- clients.csv: Per-client/per-round metrics (fit duration, samples)
- summary.csv: Per-run aggregated metrics (TTA, p50/p95/p99, failure rate)
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
import numpy as np


def parse_server_log(log_file: Path) -> Dict:
    """Parse server log and extract round metrics"""
    rounds = []
    run_meta = {}
    
    with open(log_file) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            
            event = entry.get("event")
            
            if event == "experiment_start":
                run_meta["run_id"] = entry.get("run_id", "unknown")
                # Extract SEC/NET from run_id (format: SEC0_NET0_timestamp)
                run_id = entry.get("run_id", "unknown")
                if "_" in run_id:
                    parts = run_id.split("_")
                    run_meta["sec_level"] = parts[0] if len(parts) > 0 else "unknown"
                    run_meta["net_profile"] = parts[1] if len(parts) > 1 else "unknown"
                else:
                    run_meta["sec_level"] = "unknown"
                    run_meta["net_profile"] = "unknown"
                
            elif event == "round_start":
                rounds.append({
                    "round_id": entry.get("round"),
                    "start_ts": entry.get("timestamp")
                })
            
            elif event == "round_end":
                round_id = entry.get("round")
                # Find matching start
                for r in rounds:
                    if r["round_id"] == round_id and "end_ts" not in r:
                        r["end_ts"] = entry.get("timestamp")
                        r["accuracy"] = entry.get("test_accuracy", 0)
                        r["loss"] = entry.get("test_loss", 0)
                        r["failures"] = entry.get("num_failures", 0)
                        break
            
            elif event == "target_accuracy_reached":
                # Store TTA milestone
                target = entry.get("target_accuracy")
                ts = entry.get("timestamp")
                if target and ts:
                    run_meta[f"tta_{int(target*100)}"] = ts
    
    # Calculate durations
    for r in rounds:
        if "start_ts" in r and "end_ts" in r:
            try:
                start = datetime.fromisoformat(r["start_ts"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(r["end_ts"].replace("Z", "+00:00"))
                r["duration"] = (end - start).total_seconds()
            except:
                r["duration"] = None
    
    return {
        "meta": run_meta,
        "rounds": rounds
    }


def parse_client_log(log_file: Path, client_id: int) -> List[Dict]:
    """Parse client log and extract fit metrics"""
    fit_records = []
    
    with open(log_file) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            
            event = entry.get("event")
            
            if event == "fit_end":
                fit_records.append({
                    "client_id": client_id,
                    "round_id": entry.get("round_id", -1),
                    "fit_duration": entry.get("duration_sec"),
                    "train_loss": entry.get("train_loss"),
                    "num_samples": entry.get("num_samples")
                })
    
    return fit_records


def compute_tta(rounds: List[Dict], target_acc: float = 0.95) -> Optional[float]:
    """Compute Time-To-Accuracy (seconds to reach target accuracy)"""
    for r in rounds:
        if r.get("accuracy", 0) >= target_acc and r.get("end_ts"):
            try:
                ts = datetime.fromisoformat(r["end_ts"].replace("Z", "+00:00"))
                # Compute from first round start
                first_start = datetime.fromisoformat(rounds[0]["start_ts"].replace("Z", "+00:00"))
                return (ts - first_start).total_seconds()
            except:
                continue
    return None


def parse_run(run_dir: Path) -> Dict:
    """Parse all logs in a run directory"""
    result = {
        "meta": {},
        "rounds_df": None,
        "clients_df": None,
        "summary": {}
    }
    
    # Find server log
    server_logs = list(run_dir.glob("server_*.log"))
    if not server_logs:
        print(f"Warning: No server log in {run_dir}")
        return result
    
    # Parse server
    server_data = parse_server_log(server_logs[0])
    result["meta"] = server_data["meta"]
    
    # Create rounds DataFrame
    if server_data["rounds"]:
        rounds_df = pd.DataFrame(server_data["rounds"])
        rounds_df["run_id"] = result["meta"].get("run_id", run_dir.name)
        result["rounds_df"] = rounds_df
    
    # Parse clients
    client_records = []
    for client_log in sorted(run_dir.glob("fl-client-*.log")):
        # Extract client ID from filename: fl-client-1_<run_id>.log
        try:
            client_id = int(client_log.stem.split("-")[2].split("_")[0])
        except:
            client_id = -1
        
        client_data = parse_client_log(client_log, client_id)
        client_records.extend(client_data)
    
    if client_records:
        clients_df = pd.DataFrame(client_records)
        clients_df["run_id"] = result["meta"].get("run_id", run_dir.name)
        result["clients_df"] = clients_df
    
    # Compute summary stats
    if result["rounds_df"] is not None:
        rounds_df = result["rounds_df"]
        durations = rounds_df["duration"].dropna()
        accuracies = rounds_df["accuracy"].dropna()
        
        result["summary"] = {
            "run_id": result["meta"].get("run_id", run_dir.name),
            "sec_level": result["meta"].get("sec_level", "unknown"),
            "net_profile": result["meta"].get("net_profile", "unknown"),
            "iid": True,  # Extract from metadata if available
            "data_seed": 42,
            "num_rounds": len(rounds_df),
            "final_accuracy": accuracies.iloc[-1] if len(accuracies) > 0 else None,
            "tta_95": compute_tta(server_data["rounds"], 0.95),
            "tta_97": compute_tta(server_data["rounds"], 0.97),
            "p50_round": durations.quantile(0.50) if len(durations) > 0 else None,
            "p95_round": durations.quantile(0.95) if len(durations) > 0 else None,
            "p99_round": durations.quantile(0.99) if len(durations) > 0 else None,
            "mean_round": durations.mean() if len(durations) > 0 else None,
            "std_round": durations.std() if len(durations) > 0 else None,
            "failure_rate": rounds_df["failures"].sum() / len(rounds_df) if len(rounds_df) > 0 else 0
        }
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Parse FL logs to CSV")
    parser.add_argument("--log-dir", type=Path, required=True, help="Directory containing run logs")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory for CSVs")
    parser.add_argument("--run-id", type=str, help="Specific run ID to parse (default: all)")
    
    args = parser.parse_args()
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all run directories
    if args.run_id:
        run_dirs = [args.log_dir / args.run_id]
    else:
        run_dirs = [d for d in args.log_dir.iterdir() if d.is_dir()]
    
    if not run_dirs:
        print(f"No run directories found in {args.log_dir}")
        sys.exit(1)
    
    print(f"Found {len(run_dirs)} run(s) to parse")
    
    # Parse all runs
    all_rounds = []
    all_clients = []
    all_summaries = []
    
    for run_dir in sorted(run_dirs):
        print(f"Parsing {run_dir.name}...")
        result = parse_run(run_dir)
        
        if result["rounds_df"] is not None:
            all_rounds.append(result["rounds_df"])
        
        if result["clients_df"] is not None:
            all_clients.append(result["clients_df"])
        
        if result["summary"]:
            all_summaries.append(result["summary"])
    
    # Concatenate and save
    if all_rounds:
        rounds_df = pd.concat(all_rounds, ignore_index=True)
        rounds_csv = args.output_dir / "rounds.csv"
        rounds_df.to_csv(rounds_csv, index=False)
        print(f"✅ Saved {len(rounds_df)} rounds to {rounds_csv}")
    
    if all_clients:
        clients_df = pd.concat(all_clients, ignore_index=True)
        clients_csv = args.output_dir / "clients.csv"
        clients_df.to_csv(clients_csv, index=False)
        print(f"✅ Saved {len(clients_df)} client records to {clients_csv}")
    
    if all_summaries:
        summary_df = pd.DataFrame(all_summaries)
        summary_csv = args.output_dir / "summary.csv"
        summary_df.to_csv(summary_csv, index=False)
        print(f"✅ Saved {len(summary_df)} run summaries to {summary_csv}")
    
    print("\n📊 Parsing complete!")


if __name__ == "__main__":
    main()
