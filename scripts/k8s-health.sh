#!/bin/bash
# NexusForge AI — K8s Health Check
# Shows status of all NexusForge resources in the cluster

echo "=== NexusForge K8s Health Check ==="
echo ""

# Check if namespace exists
if ! kubectl get namespace nexusforge &>/dev/null; then
    echo "ERROR: Namespace 'nexusforge' not found. Is NexusForge deployed?"
    echo "Run: ./scripts/k8s-local-deploy.sh"
    exit 1
fi

echo "--- Pods ---"
kubectl -n nexusforge get pods -o wide
echo ""

echo "--- Services ---"
kubectl -n nexusforge get svc
echo ""

echo "--- Deployments ---"
kubectl -n nexusforge get deployments
echo ""

echo "--- StatefulSets ---"
kubectl -n nexusforge get statefulsets
echo ""

echo "--- HPAs ---"
kubectl -n nexusforge get hpa 2>/dev/null || echo "No HPAs found"
echo ""

echo "--- Resource Usage ---"
kubectl -n nexusforge top pods 2>/dev/null || echo "Metrics server not available (install metrics-server for resource usage)"
echo ""

echo "--- Events (last 10) ---"
kubectl -n nexusforge get events --sort-by='.lastTimestamp' 2>/dev/null | tail -10
echo ""

# Quick health endpoint check
echo "--- Endpoint Health ---"
GATEWAY_POD=$(kubectl -n nexusforge get pods -l app=gateway -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$GATEWAY_POD" ]; then
    kubectl -n nexusforge exec "$GATEWAY_POD" -- wget -qO- http://localhost:8000/health 2>/dev/null || echo "Gateway health endpoint not responding (may need port-forward)"
else
    echo "No gateway pod found"
fi
