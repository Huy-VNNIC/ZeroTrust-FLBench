#!/usr/bin/env python3
"""
Validate data split correctness (no overlapping samples between clients)

Usage:
    python scripts/validate_splits.py --num-clients 5 --data-seed 42 --iid
"""

import argparse
import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fl_client import create_iid_split, create_noniid_split
from torchvision import datasets, transforms


def validate_iid_split(num_clients: int, data_seed: int):
    """Validate IID split has no overlapping indices"""
    print(f"\n{'='*60}")
    print(f"Validating IID Split")
    print(f"  Clients: {num_clients}, Data Seed: {data_seed}")
    print(f"{'='*60}")
    
    # Load dataset to get size
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    
    trainset = datasets.MNIST(
        "/tmp/mnist",
        train=True,
        download=True,
        transform=transform
    )
    
    dataset_size = len(trainset)
    print(f"Dataset size: {dataset_size}")
    
    # Get splits for all clients
    all_indices = []
    client_sizes = []
    
    for client_id in range(num_clients):
        indices = create_iid_split(dataset_size, num_clients, client_id, data_seed)
        all_indices.extend(indices)
        client_sizes.append(len(indices))
        print(f"  Client {client_id}: {len(indices)} samples")
    
    # Check for duplicates
    unique_indices = set(all_indices)
    
    print(f"\nValidation Results:")
    print(f"  Total indices collected: {len(all_indices)}")
    print(f"  Unique indices: {len(unique_indices)}")
    print(f"  Expected (dataset size): {dataset_size}")
    
    # Assertions
    has_duplicates = len(all_indices) != len(unique_indices)
    missing_samples = len(unique_indices) != dataset_size
    
    if has_duplicates:
        print(f"  ❌ FAIL: Found {len(all_indices) - len(unique_indices)} duplicate indices!")
        return False
    
    if missing_samples:
        print(f"  ❌ FAIL: Missing {dataset_size - len(unique_indices)} samples!")
        return False
    
    print(f"  ✅ PASS: No duplicates, all samples assigned")
    
    # Check balance
    sizes = np.array(client_sizes)
    mean_size = sizes.mean()
    std_size = sizes.std()
    print(f"\nBalance Check:")
    print(f"  Mean samples per client: {mean_size:.1f}")
    print(f"  Std deviation: {std_size:.1f}")
    print(f"  Min: {sizes.min()}, Max: {sizes.max()}")
    
    return True


def validate_noniid_split(num_clients: int, alpha: float, data_seed: int):
    """Validate Non-IID split has no overlapping indices"""
    print(f"\n{'='*60}")
    print(f"Validating Non-IID Split (Dirichlet)")
    print(f"  Clients: {num_clients}, Alpha: {alpha}, Data Seed: {data_seed}")
    print(f"{'='*60}")
    
    # Load dataset to get labels
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    
    trainset = datasets.MNIST(
        "/tmp/mnist",
        train=True,
        download=True,
        transform=transform
    )
    
    labels = trainset.targets.numpy()
    dataset_size = len(labels)
    print(f"Dataset size: {dataset_size}")
    
    # Get splits for all clients
    all_indices = []
    client_sizes = []
    client_label_dist = []
    
    for client_id in range(num_clients):
        indices = create_noniid_split(labels, num_clients, client_id, alpha, data_seed)
        all_indices.extend(indices)
        client_sizes.append(len(indices))
        
        # Count label distribution
        client_labels = labels[indices]
        label_counts = np.bincount(client_labels, minlength=10)
        client_label_dist.append(label_counts)
        
        print(f"  Client {client_id}: {len(indices)} samples")
        print(f"    Label distribution: {label_counts}")
    
    # Check for duplicates
    unique_indices = set(all_indices)
    
    print(f"\nValidation Results:")
    print(f"  Total indices collected: {len(all_indices)}")
    print(f"  Unique indices: {len(unique_indices)}")
    print(f"  Expected (dataset size): {dataset_size}")
    
    # Assertions
    has_duplicates = len(all_indices) != len(unique_indices)
    missing_samples = len(unique_indices) != dataset_size
    
    if has_duplicates:
        print(f"  ❌ FAIL: Found {len(all_indices) - len(unique_indices)} duplicate indices!")
        return False
    
    if missing_samples:
        print(f"  ❌ FAIL: Missing {dataset_size - len(unique_indices)} samples!")
        return False
    
    print(f"  ✅ PASS: No duplicates, all samples assigned")
    
    # Check skewness
    label_dist = np.array(client_label_dist)
    print(f"\nSkewness Analysis:")
    print(f"  Alpha (lower = more skewed): {alpha}")
    
    # Jensen-Shannon divergence from uniform
    uniform = np.ones(10) / 10
    divergences = []
    for i, dist in enumerate(label_dist):
        if dist.sum() > 0:
            p = dist / dist.sum()
            # Simple KL-like metric
            nonzero = p > 0
            kl = (p[nonzero] * np.log(p[nonzero] / uniform[nonzero])).sum()
            divergences.append(kl)
            print(f"  Client {i} KL-divergence: {kl:.3f}")
    
    avg_divergence = np.mean(divergences)
    print(f"  Average KL-divergence: {avg_divergence:.3f}")
    print(f"  (Higher = more skewed. Baseline uniform = 0.0)")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Validate data split correctness"
    )
    parser.add_argument("--num-clients", type=int, default=5)
    parser.add_argument("--data-seed", type=int, default=42)
    parser.add_argument("--iid", action="store_true", help="Test IID split")
    parser.add_argument("--noniid", action="store_true", help="Test Non-IID split")
    parser.add_argument("--alpha", type=float, default=0.5)
    
    args = parser.parse_args()
    
    # Default: test both if neither specified
    if not args.iid and not args.noniid:
        args.iid = True
        args.noniid = True
    
    success = True
    
    if args.iid:
        if not validate_iid_split(args.num_clients, args.data_seed):
            success = False
    
    if args.noniid:
        if not validate_noniid_split(args.num_clients, args.alpha, args.data_seed):
            success = False
    
    print(f"\n{'='*60}")
    if success:
        print("✅ All validations PASSED")
        sys.exit(0)
    else:
        print("❌ Some validations FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
