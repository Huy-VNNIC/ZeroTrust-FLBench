# NetworkPolicy Configurations

This directory contains Kubernetes NetworkPolicy manifests for **SEC1** (NetworkPolicy only) and **SEC3** (NetworkPolicy + mTLS).

## Overview

In default Kubernetes, all pods can communicate with all other pods (flat networking). This poses security risks for FL, as identified by the kubeFlower paper.

**Our approach:** Default-deny + explicit allow-list for FL communication.

## SEC1: NetworkPolicy Only

Apply default-deny, then allow only necessary flows:

1. **Clients → Server** (gRPC on port 8080)
2. **Server → Clients** (response traffic)
3. **All → DNS** (for service discovery)
4. **All → Prometheus** (for metrics scraping, if enabled)

## NetworkPolicy Rules

### 1. Default Deny All Ingress/Egress

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: fl-experiment
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

**Effect:** Blocks all traffic by default.

### 2. Allow Clients → Server

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-clients-to-server
  namespace: fl-experiment
spec:
  podSelector:
    matchLabels:
      app: fl-server
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: fl-client
    ports:
    - protocol: TCP
      port: 8080
```

### 3. Allow Clients Egress to Server

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-clients-egress-to-server
  namespace: fl-experiment
spec:
  podSelector:
    matchLabels:
      app: fl-client
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: fl-server
    ports:
    - protocol: TCP
      port: 8080
```

### 4. Allow DNS

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: fl-experiment
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
```

### 5. Allow Metrics Scraping (Optional)

If Prometheus is in a different namespace:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prometheus-scrape
  namespace: fl-experiment
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 8000  # Adjust based on metrics port
```

## Deployment

### Apply SEC1

```bash
# Deploy baseline FL first
kubectl apply -f k8s/00-baseline/

# Apply NetworkPolicy
kubectl apply -f k8s/10-networkpolicy/
```

### Verify

```bash
# Check policies
kubectl get networkpolicies -n fl-experiment

# Test connectivity from client to server
kubectl exec -n fl-experiment fl-client-0 -- curl fl-server:8080

# Should succeed

# Test connectivity from client to another client (should fail)
kubectl exec -n fl-experiment fl-client-0 -- curl fl-client-1:8080

# Should timeout or be denied
```

## Common Issues

### Issue 1: DNS Not Working

**Symptom:** Clients can't resolve `fl-server` hostname.

**Fix:** Ensure DNS policy allows egress to kube-system namespace.

**Debug:**
```bash
kubectl exec -n fl-experiment fl-client-0 -- nslookup fl-server
```

### Issue 2: Metrics Scraping Blocked

**Symptom:** Prometheus can't scrape metrics from FL pods.

**Fix:** Add ingress rule for Prometheus namespace.

### Issue 3: Blocked Initial Handshake

**Symptom:** Clients connect but hang during gRPC handshake.

**Fix:** Ensure bidirectional egress/ingress rules for both client→server and server→client.

## Logging Blocked Connections

To debug, you can enable NetworkPolicy logging (if your CNI supports it):

```bash
# For Calico
kubectl annotate networkpolicy -n fl-experiment default-deny-all \
  projectcalico.org/metadata='{"log": "all"}'
```

Then check node logs for denied packets.

## Comparison: SEC0 vs SEC1

| Metric | SEC0 (No Policy) | SEC1 (NetworkPolicy) | Expected Change |
|--------|------------------|----------------------|-----------------|
| Round Latency | Baseline | +0-5% | Minimal (only initial DNS/connection) |
| Failure Rate | Low | Slightly higher | DNS misconfig can cause failures |
| Security | ❌ Flat network | ✅ Segmented | Prevents lateral movement |

**Key insight:** If configured correctly, NetworkPolicy should have minimal performance impact but significantly improves security posture.

## Next Steps

After validating SEC1, proceed to:
- **SEC2:** Add mTLS without NetworkPolicy (k8s/20-mtls-linkerd/)
- **SEC3:** Combine NetworkPolicy + mTLS

---

**Last updated:** 2026-02-02
