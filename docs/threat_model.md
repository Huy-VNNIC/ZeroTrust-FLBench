# Threat Model and Scope

## 1. Scope Definition

This project evaluates **Zero-Trust networking mechanisms** in Kubernetes-based Federated Learning (FL) deployments. We focus on **systems and network security**, not cryptographic security of FL algorithms.

### What We Evaluate

1. **Network Isolation:** Kubernetes NetworkPolicy with default-deny + allow-list
2. **mTLS in Transit:** Service mesh (Linkerd/Istio) for authenticated communication
3. **Multi-tenant Isolation:** Namespace-level separation (optional extension)

### What We Do NOT Cover

- FL model poisoning attacks
- Differential privacy mechanisms
- Byzantine-robust aggregation
- Client authentication/authorization at application level
- Data privacy guarantees

## 2. Threat Model

### Assumed Adversary

**Malicious FL Client** with the following capabilities:

- Can join FL training as a legitimate client
- Has network access within Kubernetes cluster (pod-to-pod)
- Can attempt lateral movement/scanning
- Can eavesdrop on unencrypted traffic
- **Cannot** compromise the control plane or node OS

### Attack Scenarios We Address

#### Scenario 1: Flat Networking Exploitation

**Problem:** In default Kubernetes, all pods can talk to all pods.

- Malicious client can scan/probe other clients or server
- Can access services not intended for FL clients (metrics, admin APIs)
- Can attempt MITM attacks on unencrypted gRPC/HTTP

**Mitigation:** NetworkPolicy default-deny + allow-list

**Reference:** kubeFlower paper demonstrated this risk ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0167739X24001134))

#### Scenario 2: Traffic Eavesdropping

**Problem:** Model updates transmitted in plaintext can leak training data information.

- Gradient updates contain information about training samples
- Network sniffing within cluster namespace

**Mitigation:** mTLS via service mesh

#### Scenario 3: Unauthorized Access

**Problem:** Without mutual authentication, a rogue pod can impersonate clients or server.

**Mitigation:** mTLS certificate-based identity

### Out-of-Scope Threats

- **Node compromise:** Assume nodes are trusted
- **Control plane attacks:** Assume K8s API server is secured
- **Application-level exploits:** Assume FL server/client code has no RCE vulnerabilities
- **Side-channel attacks:** Timing, cache, etc.

## 3. Zero-Trust Principles Applied

We implement **subset of Zero-Trust** relevant to FL networking:

1. **Least Privilege Network Access:** Only allow explicitly required flows
2. **Verify Explicitly:** mTLS for all FL communication
3. **Assume Breach:** Default-deny, segmentation to limit blast radius

## 4. Comparison with Prior Work

| Work | Focus | Gap |
|------|-------|-----|
| kubeFlower | Privacy risks in K8s FL | Identified problem, no systematic evaluation |
| Service mesh benchmarks | mTLS overhead | Generic workloads, not FL-specific metrics |
| This work | **Design-space + FL metrics** | Combines security + FL performance + edge conditions |

## 5. Why This Matters

### For Practitioners

- **Deployment guidance:** What security measures to enable for edge FL?
- **Performance expectations:** How much overhead to budget for zero-trust?
- **Failure modes:** What breaks when you enable default-deny or mTLS?

### For Researchers

- **Measurement methodology:** How to properly measure FL under network security constraints
- **Trade-off space:** Quantify security vs. performance vs. learning quality
- **Reproducibility:** Open benchmark for future work

## 6. Success Criteria

This work is successful if it provides:

1. **Clear design-space map:** {security config} × {network conditions} → {FL metrics}
2. **Actionable guidelines:** "If your edge has >1% loss, use SEC1 not SEC3 because..."
3. **Reproducible harness:** Others can run the same experiments

**Note:** Even "negative results" (e.g., "mTLS breaks FL under high jitter") are valuable contributions if measured rigorously.

## 7. Ethical Considerations

- All experiments run on controlled infrastructure
- No real user data involved (MNIST/CIFAR-10)
- Open-source artifacts to enable reproducible research

## 8. Limitations (Acknowledged Upfront)

- **Simulated edge conditions:** Using `tc/netem`, not real edge devices
- **Small scale:** 5-10 clients (laptop-feasible), not 100s of clients
- **Workload scope:** Vision tasks (MNIST/CIFAR), not NLP or large models
- **Single cluster:** Not multi-cluster/cross-region FL

These limitations are **acceptable** for a systems measurement paper if we:
- State them clearly
- Show results generalize across multiple workloads (W1/W2)
- Provide methodology for future large-scale studies

---

**Status:** Living document, updated as experiments reveal insights.

**Last updated:** 2026-02-02
