"""
ZeroTrust-FLBench: Federated Learning Client (FIXED VERSION)
Uses Flower framework with enhanced logging

CRITICAL FIXES:
1. Data split uses SHARED seed for non-overlapping partitions
2. Model returns logits (not log_softmax) for CrossEntropyLoss
3. Proper IID and Non-IID split functions
"""

import time
import json
import logging
import os
from typing import Tuple, Dict

import flwr as fl
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms
import numpy as np

# Configure structured JSON logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger("fl_client")


class SimpleCNN(nn.Module):
    """Simple CNN for MNIST"""
    def __init__(self):
        super(SimpleCNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.dropout1 = nn.Dropout(0.25)
        self.dropout2 = nn.Dropout(0.5)
        self.fc1 = nn.Linear(9216, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = self.conv1(x)
        x = F.relu(x)
        x = self.conv2(x)
        x = F.relu(x)
        x = F.max_pool2d(x, 2)
        self.dropout1(x)
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        x = F.relu(x)
        x = self.dropout2(x)
        x = self.fc2(x)
        # FIX: Return logits (not log_softmax) for CrossEntropyLoss
        return x


def create_iid_split(
    dataset_size: int,
    num_clients: int,
    client_id: int,
    data_seed: int
) -> np.ndarray:
    """
    Create IID split with SHARED seed (all clients use same partition)
    
    CRITICAL: All clients must call this with same data_seed to get
    non-overlapping, deterministic splits
    
    Args:
        dataset_size: Total number of samples
        num_clients: Total number of clients
        client_id: This client's ID
        data_seed: Shared seed for reproducibility
    
    Returns:
        Indices for this client
    """
    # Use SHARED seed to create same random permutation for all clients
    rng = np.random.RandomState(data_seed)
    indices = np.arange(dataset_size)
    rng.shuffle(indices)
    
    # Split into num_clients parts (deterministic)
    splits = np.array_split(indices, num_clients)
    
    # Convert 1-based client_id to 0-based index
    return splits[client_id - 1]


def create_noniid_split(
    labels: np.ndarray,
    num_clients: int,
    client_id: int,
    alpha: float,
    data_seed: int
) -> np.ndarray:
    """
    Create Non-IID split using Dirichlet distribution with SHARED seed
    
    CRITICAL: All clients must call this with same data_seed to get
    the same Dirichlet distribution and non-overlapping splits
    
    Args:
        labels: Array of all training labels
        num_clients: Total number of clients
        client_id: This client's ID
        alpha: Dirichlet concentration (lower = more skewed)
        data_seed: Shared seed for reproducibility
    
    Returns:
        Indices for this client
    """
    num_classes = len(np.unique(labels))
    
    # FIX: Use SHARED seed (critical!)
    rng = np.random.RandomState(data_seed)
    
    # Create Dirichlet distribution per class (same for all clients)
    label_distribution = rng.dirichlet([alpha] * num_clients, num_classes)
    
    # Assign samples to clients based on distribution
    client_indices = []
    
    for class_id in range(num_classes):
        class_indices = np.where(labels == class_id)[0]
        # Shuffle with same seed
        rng.shuffle(class_indices)
        
        # Split this class's samples according to Dirichlet proportions
        splits = np.cumsum(label_distribution[class_id])
        splits = (splits * len(class_indices)).astype(int)
        
        start_idx = 0 if client_id == 0 else splits[client_id - 1]
        end_idx = splits[client_id]
        
        client_indices.extend(class_indices[start_idx:end_idx])
    
    return np.array(client_indices)


def load_data(
    client_id: int, 
    num_clients: int, 
    iid: bool = True,
    alpha: float = 0.5,
    data_seed: int = 42
) -> Tuple[DataLoader, DataLoader]:
    """
    Load and partition MNIST data for a specific client
    
    CRITICAL: Uses shared data_seed for deterministic, non-overlapping splits
    
    Args:
        client_id: Client identifier (0 to num_clients-1)
        num_clients: Total number of clients
        iid: If True, use IID split; if False, use Non-IID Dirichlet split
        alpha: Dirichlet concentration parameter (lower = more skewed)
        data_seed: Shared seed for deterministic data partitioning
    """
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    
    # Load full training set
    trainset = datasets.MNIST(
        "/data/mnist",
        train=True,
        download=True,
        transform=transform
    )
    
    testset = datasets.MNIST(
        "/data/mnist",
        train=False,
        download=True,
        transform=transform
    )
    
    # FIX: Create data partition with SHARED seed (critical for reproducibility)
    if iid:
        # IID split: uniform random partition with shared seed
        client_indices = create_iid_split(
            len(trainset),
            num_clients,
            client_id,
            data_seed
        )
    else:
        # Non-IID split: Dirichlet allocation with shared seed
        client_indices = create_noniid_split(
            trainset.targets.numpy(),
            num_clients,
            client_id,
            alpha,
            data_seed
        )
    
    # Create client's training subset
    client_trainset = Subset(trainset, client_indices)
    
    # Each client gets the same test set (for local validation if needed)
    trainloader = DataLoader(client_trainset, batch_size=32, shuffle=True)
    testloader = DataLoader(testset, batch_size=128, shuffle=False)
    
    logger.info(json.dumps({
        "event": "data_loaded",
        "client_id": client_id,
        "num_samples": len(client_indices),
        "iid": iid,
        "alpha": alpha if not iid else None,
        "data_seed": data_seed,
        "timestamp": time.time()
    }))
    
    return trainloader, testloader


def train(
    model: nn.Module,
    trainloader: DataLoader,
    epochs: int,
    device: torch.device
) -> Tuple[int, float]:
    """Train model for specified epochs"""
    # FIX: CrossEntropyLoss expects logits (not log_softmax)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01, momentum=0.9)
    
    model.train()
    total_samples = 0
    total_loss = 0.0
    
    for epoch in range(epochs):
        for batch_idx, (data, target) in enumerate(trainloader):
            data, target = data.to(device), target.to(device)
            
            optimizer.zero_grad()
            output = model(data)  # logits
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            
            total_samples += len(data)
            total_loss += loss.item() * len(data)
    
    avg_loss = total_loss / total_samples
    return total_samples, avg_loss


def test(
    model: nn.Module,
    testloader: DataLoader,
    device: torch.device
) -> Tuple[float, float]:
    """Evaluate model on test set"""
    criterion = nn.CrossEntropyLoss(reduction='sum')
    model.eval()
    test_loss = 0
    correct = 0
    
    with torch.no_grad():
        for data, target in testloader:
            data, target = data.to(device), target.to(device)
            output = model(data)  # logits
            test_loss += criterion(output, target).item()
            pred = output.argmax(dim=1, keepdim=True)
            correct += pred.eq(target.view_as(pred)).sum().item()
    
    test_loss /= len(testloader.dataset)
    accuracy = 100. * correct / len(testloader.dataset)
    
    return test_loss, accuracy


class FlowerClient(fl.client.NumPyClient):
    """Flower client with logging"""
    
    def __init__(
        self,
        client_id: int,
        num_clients: int,
        trainloader: DataLoader,
        testloader: DataLoader
    ):
        self.client_id = client_id
        self.num_clients = num_clients
        self.trainloader = trainloader
        self.testloader = testloader
        self.model = SimpleCNN()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
        logger.info(json.dumps({
            "event": "client_init",
            "client_id": client_id,
            "device": str(self.device),
            "num_train_samples": len(trainloader.dataset),
            "timestamp": time.time()
        }))
    
    def get_parameters(self, config):
        """Return model parameters as numpy arrays"""
        return [val.cpu().numpy() for val in self.model.state_dict().values()]
    
    def set_parameters(self, parameters):
        """Update model parameters from numpy arrays"""
        params_dict = zip(self.model.state_dict().keys(), parameters)
        state_dict = {k: torch.tensor(v) for k, v in params_dict}
        self.model.load_state_dict(state_dict, strict=True)
    
    def fit(self, parameters, config):
        """Train model and return updated parameters"""
        fit_start = time.time()
        
        # Extract round info from config
        round_id = config.get("server_round", -1)
        
        logger.info(json.dumps({
            "event": "fit_start",
            "client_id": self.client_id,
            "round_id": round_id,
            "timestamp": fit_start
        }))
        
        # Update local model
        self.set_parameters(parameters)
        
        # Train
        num_samples, train_loss = train(
            self.model,
            self.trainloader,
            epochs=1,
            device=self.device
        )
        
        fit_end = time.time()
        
        logger.info(json.dumps({
            "event": "fit_end",
            "client_id": self.client_id,
            "round_id": round_id,
            "timestamp": fit_end,
            "duration_sec": fit_end - fit_start,
            "num_samples": num_samples,
            "train_loss": train_loss
        }))
        
        # Return updated parameters and metrics
        return (
            self.get_parameters(config={}),
            num_samples,
            {"train_loss": train_loss}
        )
    
    def evaluate(self, parameters, config):
        """Evaluate model (optional, disabled by default)"""
        self.set_parameters(parameters)
        loss, accuracy = test(self.model, self.testloader, self.device)
        
        return float(loss), len(self.testloader.dataset), {"accuracy": accuracy}


def main():
    """Start FL client"""
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", type=int, required=True)
    parser.add_argument("--num-clients", type=int, default=5)
    parser.add_argument("--server-address", type=str, default="fl-server:8080")
    parser.add_argument("--iid", action="store_true", help="Use IID data split")
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument("--data-seed", type=int, default=42, help="Shared seed for data partitioning")
    parser.add_argument("--train-seed", type=int, default=None, help="Client-specific training seed")
    args = parser.parse_args()
    
    # FIX: Set client-specific training seed (for model init and mini-batch order)
    train_seed = args.train_seed if args.train_seed is not None else (42 + args.client_id)
    torch.manual_seed(train_seed)
    np.random.seed(train_seed)
    
    logger.info(json.dumps({
        "event": "client_start",
        "client_id": args.client_id,
        "server_address": args.server_address,
        "data_seed": args.data_seed,
        "train_seed": train_seed,
        "run_id": os.getenv("RUN_ID", "unknown"),
        "timestamp": time.time()
    }))
    
    # Load data with shared data_seed (critical for non-overlapping splits)
    trainloader, testloader = load_data(
        client_id=args.client_id,
        num_clients=args.num_clients,
        iid=args.iid,
        alpha=args.alpha,
        data_seed=args.data_seed
    )
    
    # Create client
    client = FlowerClient(
        client_id=args.client_id,
        num_clients=args.num_clients,
        trainloader=trainloader,
        testloader=testloader
    )
    
    # Start Flower client
    fl.client.start_numpy_client(
        server_address=args.server_address,
        client=client
    )
    
    logger.info(json.dumps({
        "event": "client_end",
        "client_id": args.client_id,
        "timestamp": time.time()
    }))


if __name__ == "__main__":
    main()
