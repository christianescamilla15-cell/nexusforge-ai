#!/bin/bash
# NexusForge AI — K8s Evidence Capture
# Captures deployment evidence for portfolio/interview demonstrations
# Usage: ./scripts/k8s-evidence.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

EVIDENCE_DIR="docs/k8s-evidence"
mkdir -p "$EVIDENCE_DIR"

echo "=== NexusForge K8s Evidence ==="
echo "Date: $(date)"
echo "Evidence dir: $EVIDENCE_DIR"
echo ""

echo "--- Cluster Info ---"
kubectl cluster-info 2>&1 | tee "$EVIDENCE_DIR/cluster-info.txt"
echo ""

echo "--- Nodes ---"
kubectl get nodes -o wide 2>&1 | tee "$EVIDENCE_DIR/nodes.txt"
echo ""

echo "--- Namespace ---"
kubectl get namespace nexusforge 2>&1 | tee "$EVIDENCE_DIR/namespace.txt"
echo ""

echo "--- Pods ---"
kubectl -n nexusforge get pods -o wide 2>&1 | tee "$EVIDENCE_DIR/pods.txt"
echo ""

echo "--- Services ---"
kubectl -n nexusforge get svc 2>&1 | tee "$EVIDENCE_DIR/services.txt"
echo ""

echo "--- Deployments ---"
kubectl -n nexusforge get deployments 2>&1 | tee "$EVIDENCE_DIR/deployments.txt"
echo ""

echo "--- StatefulSets ---"
kubectl -n nexusforge get statefulsets 2>&1 | tee "$EVIDENCE_DIR/statefulsets.txt"
echo ""

echo "--- HPAs ---"
kubectl -n nexusforge get hpa 2>&1 | tee "$EVIDENCE_DIR/hpa.txt" || echo "No HPAs configured"
echo ""

echo "--- Resource Usage ---"
kubectl -n nexusforge top pods 2>&1 | tee "$EVIDENCE_DIR/resources.txt" || echo "Metrics server not available (normal for kind)"
echo ""

echo "--- Pod Descriptions ---"
kubectl -n nexusforge describe pods 2>&1 | tee "$EVIDENCE_DIR/pod-details.txt"
echo ""

echo "--- Health Check (Backend) ---"
curl -s http://localhost:8080/health 2>/dev/null | tee "$EVIDENCE_DIR/health-backend.json" || echo "Backend not reachable via NodePort"
echo ""

echo "--- Health Check (Frontend) ---"
curl -s -o /dev/null -w "HTTP Status: %{http_code}" http://localhost:3000 2>/dev/null | tee "$EVIDENCE_DIR/health-frontend.txt" || echo "Frontend not reachable via NodePort"
echo ""

echo "--- ConfigMaps ---"
kubectl -n nexusforge get configmaps 2>&1 | tee "$EVIDENCE_DIR/configmaps.txt"
echo ""

echo "--- Secrets (names only) ---"
kubectl -n nexusforge get secrets 2>&1 | tee "$EVIDENCE_DIR/secrets.txt"
echo ""

echo "========================================="
echo "Evidence saved to $EVIDENCE_DIR/"
echo ""
ls -la "$EVIDENCE_DIR/"
echo "========================================="
