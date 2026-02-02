"""
ZeroTrust-FLBench: Federated Learning Server
Uses Flower framework for FL orchestration with enhanced logging
"""

import time
import json
import logging
from typing import List, Tuple, Dict, Optional
from pathlib import Path

import flwr as fl
from flwr.common import Metrics, FitRes, Parameters
from flwr.server.strategy import FedAvg
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import datasets, transforms

# Configure structured JSON logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # JSON only, no extra formatting
)
logger = logging.getLogger("fl_server")


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
        x = self.dropout1(x)
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        x = F.relu(x)
        x = self.dropout2(x)
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)


def load_test_data():
    """Load MNIST test set for global evaluation"""
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    
    testset = datasets.MNIST(
        "/data/mnist", 
        train=False, 
        download=True, 
        transform=transform
    )
    
    testloader = torch.utils.data.DataLoader(
        testset, 
        batch_size=128, 
        shuffle=False
    )
    
    return testloader


def evaluate_global_model(
    model: nn.Module, 
    testloader: torch.utils.data.DataLoader,
    device: torch.device
) -> Tuple[float, float]:
    """Evaluate model on test set"""
    model.eval()
    test_loss = 0
    correct = 0
    
    with torch.no_grad():
        for data, target in testloader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            test_loss += F.nll_loss(output, target, reduction='sum').item()
            pred = output.argmax(dim=1, keepdim=True)
            correct += pred.eq(target.view_as(pred)).sum().item()
    
    test_loss /= len(testloader.dataset)
    accuracy = 100. * correct / len(testloader.dataset)
    
    return test_loss, accuracy


class LoggingFedAvg(FedAvg):
    """
    FedAvg strategy with comprehensive logging for measurement
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.round_start_time = None
        self.training_start_time = time.time()
        
        # Track time-to-target-accuracy
        self.target_accuracies = [95.0, 97.0, 98.0]
        self.tta_reached = {acc: None for acc in self.target_accuracies}
        
        # Track model and data for evaluation
        self.model = SimpleCNN()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.testloader = load_test_data()
    
    def configure_fit(
        self, server_round: int, parameters: Parameters, client_manager
    ):
        """Log round start and configure clients"""
        self.round_start_time = time.time()
        
        logger.info(json.dumps({
            "event": "round_start",
            "round_id": server_round,
            "timestamp": self.round_start_time,
            "wall_time_since_start": self.round_start_time - self.training_start_time
        }))
        
        return super().configure_fit(server_round, parameters, client_manager)
    
    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[fl.server.client_proxy.ClientProxy, FitRes]],
        failures: List[BaseException],
    ):
        """Aggregate and log round end metrics"""
        round_end_time = time.time()
        round_duration = round_end_time - self.round_start_time
        
        # Perform aggregation
        aggregated_parameters, aggregated_metrics = super().aggregate_fit(
            server_round, results, failures
        )
        
        # Evaluate global model
        self.model.load_state_dict(
            self._parameters_to_state_dict(aggregated_parameters)
        )
        test_loss, accuracy = evaluate_global_model(
            self.model, self.testloader, self.device
        )
        
        # Check TTA milestones
        for target_acc in self.target_accuracies:
            if accuracy >= target_acc and self.tta_reached[target_acc] is None:
                self.tta_reached[target_acc] = round_end_time - self.training_start_time
                logger.info(json.dumps({
                    "event": "target_accuracy_reached",
                    "target_accuracy": target_acc,
                    "actual_accuracy": accuracy,
                    "round_id": server_round,
                    "time_to_accuracy": self.tta_reached[target_acc],
                    "timestamp": round_end_time
                }))
        
        # Log round completion
        logger.info(json.dumps({
            "event": "round_end",
            "round_id": server_round,
            "timestamp": round_end_time,
            "round_duration_sec": round_duration,
            "num_clients_success": len(results),
            "num_clients_failed": len(failures),
            "test_loss": test_loss,
            "test_accuracy": accuracy,
            "wall_time_since_start": round_end_time - self.training_start_time
        }))
        
        return aggregated_parameters, aggregated_metrics
    
    def _parameters_to_state_dict(self, parameters: Parameters) -> Dict:
        """
        Convert Flower parameters to PyTorch state dict
        
        FIX: Use flwr.common.parameters_to_ndarrays() - Parameters.tensors are BYTES, not ndarrays
        See: https://flower.ai/docs/framework/ref-api/flwr.common.html#flwr.common.Parameters
        """
        from flwr.common import parameters_to_ndarrays
        
        # Convert Parameters to list of numpy arrays (handles bytes->ndarray conversion)
        params_arrays = parameters_to_ndarrays(parameters)
        params_dict = {}
        
        # Map parameter arrays to model layers
        state_dict_keys = list(self.model.state_dict().keys())
        for key, param_array in zip(state_dict_keys, params_arrays):
            params_dict[key] = torch.from_numpy(param_array)
        
        return params_dict


def main():
    """Start FL server with logging"""
    import argparse
    import os
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-rounds", type=int, default=50)
    parser.add_argument("--min-clients", type=int, default=5)
    parser.add_argument("--fraction-fit", type=float, default=1.0)
    parser.add_argument("--fraction-evaluate", type=float, default=0.0)
    parser.add_argument("--server-address", type=str, default="0.0.0.0:8080")
    args = parser.parse_args()
    
    # Log experiment start
    logger.info(json.dumps({
        "event": "experiment_start",
        "timestamp": time.time(),
        "config": {
            "num_rounds": args.num_rounds,
            "min_clients": args.min_clients,
            "fraction_fit": args.fraction_fit,
            "server_address": args.server_address,
            "run_id": os.getenv("RUN_ID", "unknown")
        }
    }))
    
    # Create strategy
    strategy = LoggingFedAvg(
        min_available_clients=args.min_clients,
        fraction_fit=args.fraction_fit,
        fraction_evaluate=args.fraction_evaluate,
    )
    
    # Start server
    fl.server.start_server(
        server_address=args.server_address,
        config=fl.server.ServerConfig(num_rounds=args.num_rounds),
        strategy=strategy,
    )
    
    # Log experiment end
    logger.info(json.dumps({
        "event": "experiment_end",
        "timestamp": time.time(),
        "tta_results": strategy.tta_reached
    }))


if __name__ == "__main__":
    main()
