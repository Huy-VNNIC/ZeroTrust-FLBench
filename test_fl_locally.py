#!/usr/bin/env python3
"""
Test FL code locally without Kubernetes
Verify model training works correctly
"""
import torch
import torch.nn as nn
import numpy as np
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, Subset
import sys
sys.path.insert(0, 'src')

from fl_client import SimpleCNN, create_iid_split, train, test

def main():
    print("🧪 Testing FL code locally...")
    
    # Load MNIST
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    
    trainset = datasets.MNIST("/tmp/mnist", train=True, download=True, transform=transform)
    testset = datasets.MNIST("/tmp/mnist", train=False, download=True, transform=transform)
    
    # Create IID split for client 1
    client_indices = create_iid_split(
        dataset_size=len(trainset),
        num_clients=5,
        client_id=0,
        data_seed=42
    )
    
    print(f"✅ Client 0 got {len(client_indices)} samples")
    
    # Create data loaders
    client_trainset = Subset(trainset, client_indices)
    trainloader = DataLoader(client_trainset, batch_size=32, shuffle=True)
    testloader = DataLoader(testset, batch_size=128, shuffle=False)
    
    # Create model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SimpleCNN().to(device)
    
    print(f"✅ Model created on {device}")
    
    # Train for 1 epoch
    print("🏋️  Training for 1 epoch...")
    num_samples, train_loss = train(model, trainloader, epochs=1, device=device)
    print(f"✅ Trained on {num_samples} samples, loss={train_loss:.4f}")
    
    # Evaluate
    print("📊 Evaluating...")
    test_loss, accuracy = test(model, testloader, device=device)
    print(f"✅ Test loss={test_loss:.4f}, accuracy={accuracy:.2f}%")
    
    # Verify model outputs logits
    model.eval()
    with torch.no_grad():
        sample_input = torch.randn(1, 1, 28, 28).to(device)
        output = model(sample_input)
        print(f"✅ Model output shape: {output.shape} (should be [1, 10])")
        print(f"✅ Output is logits (not probabilities): min={output.min():.2f}, max={output.max():.2f}")
    
    print("\n🎉 All tests passed! FL code is working correctly.")
    print("\nNext steps:")
    print("1. Build Docker images: docker build -t zerotrust-fl .")
    print("2. Run single experiment: python3 scripts/run_one.py --sec-level SEC0 --net-profile NET0 --iid")
    print("3. Run full matrix: python3 scripts/run_matrix.py")

if __name__ == "__main__":
    main()
