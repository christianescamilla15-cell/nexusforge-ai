#!/bin/bash
# NexusForge AI — K8s Teardown
# Removes all NexusForge resources from the cluster

set -e

echo "=== Tearing down NexusForge K8s ==="
echo ""

# Delete namespace (cascades to all resources within it)
echo "Deleting namespace 'nexusforge' and all resources..."
kubectl delete namespace nexusforge --ignore-not-found --timeout=120s

# Clean up any PVCs that might remain
echo "Cleaning up persistent volume claims..."
kubectl delete pvc -l app.kubernetes.io/part-of=nexusforge --all-namespaces --ignore-not-found 2>/dev/null || true

echo ""
echo "Done. All NexusForge K8s resources removed."
