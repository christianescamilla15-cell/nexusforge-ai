#!/bin/bash
# NexusForge AI — Kind K8s One-Click Deploy
# Requires: Docker Desktop (running), kubectl
# Usage: ./scripts/k8s-kind-deploy.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== NexusForge AI — Kind K8s Deploy ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker required. Start Docker Desktop."; exit 1; }
docker info >/dev/null 2>&1 || { echo "ERROR: Docker is not running. Start Docker Desktop first."; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "ERROR: kubectl required."; exit 1; }

# Check if kind is available
KIND_CMD=""
if command -v kind >/dev/null 2>&1; then
    KIND_CMD="kind"
elif [ -f "/c/Users/Chris/kind.exe" ]; then
    KIND_CMD="/c/Users/Chris/kind.exe"
else
    echo "[0/7] Downloading kind v0.25.0..."
    curl -Lo /c/Users/Chris/kind.exe https://kind.sigs.k8s.io/dl/v0.25.0/kind-windows-amd64
    KIND_CMD="/c/Users/Chris/kind.exe"
fi

echo "Using kind: $KIND_CMD"
echo ""

# 1. Create cluster (if not exists)
echo "[1/7] Checking kind cluster..."
if ! $KIND_CMD get clusters 2>/dev/null | grep -q nexusforge; then
    echo "Creating kind cluster 'nexusforge'..."
    $KIND_CMD create cluster --config infrastructure/k8s/kind-config.yml
    echo "Cluster created."
else
    echo "Cluster 'nexusforge' already exists."
fi

# Set kubectl context
kubectl cluster-info --context kind-nexusforge >/dev/null 2>&1 || true
echo ""

# 2. Build Docker images
echo "[2/7] Building Docker images..."
echo "Building backend image..."
docker build -t nexusforge-backend:latest -f backend/Dockerfile backend/

echo "Building frontend image..."
docker build -t nexusforge-frontend:latest -f frontend/Dockerfile frontend/ 2>/dev/null || echo "WARNING: Frontend Dockerfile not found, skipping..."
echo ""

# 3. Load images into kind
echo "[3/7] Loading images into kind cluster..."
$KIND_CMD load docker-image nexusforge-backend:latest --name nexusforge
$KIND_CMD load docker-image nexusforge-frontend:latest --name nexusforge 2>/dev/null || true
echo ""

# 4. Create namespace
echo "[4/7] Creating namespace..."
kubectl apply -f infrastructure/k8s/base/namespace.yml

# 5. Apply configs and secrets
echo "[5/7] Applying configs and secrets..."
kubectl apply -f infrastructure/k8s/base/configmap.yml
kubectl apply -f infrastructure/k8s/base/secrets.yml

# 6. Deploy all services
echo "[6/7] Deploying services..."
echo "Deploying Redis..."
kubectl apply -f infrastructure/k8s/base/redis-statefulset.yml

echo "Deploying backend gateway..."
kubectl apply -f infrastructure/k8s/base/gateway-deployment.yml
kubectl apply -f infrastructure/k8s/base/gateway-service.yml

echo "Deploying workers..."
kubectl apply -f infrastructure/k8s/base/worker-deployment.yml

echo "Deploying frontend..."
kubectl apply -f infrastructure/k8s/base/frontend-deployment.yml
kubectl apply -f infrastructure/k8s/base/frontend-service.yml

echo "Skipping HPAs (not needed for local kind deployment)"
echo ""

# 7. Wait for pods
echo "[7/7] Waiting for pods to be ready..."
kubectl -n nexusforge wait --for=condition=ready pod -l app=redis --timeout=120s 2>/dev/null || echo "WARNING: Redis still starting..."
kubectl -n nexusforge wait --for=condition=ready pod -l app=gateway --timeout=120s 2>/dev/null || echo "WARNING: Gateway still starting..."
kubectl -n nexusforge wait --for=condition=ready pod -l app=frontend --timeout=120s 2>/dev/null || echo "WARNING: Frontend still starting..."

# Show status
echo ""
echo "========================================="
echo "       Deployment Status"
echo "========================================="
echo ""
echo "--- Pods ---"
kubectl -n nexusforge get pods -o wide
echo ""
echo "--- Services ---"
kubectl -n nexusforge get svc
echo ""
echo "========================================="
echo "       Access (via NodePort)"
echo "========================================="
echo ""
echo "Backend API: http://localhost:8080"
echo "  Health:    http://localhost:8080/health"
echo ""
echo "Frontend:    http://localhost:3000"
echo ""
echo "========================================="
echo "       Useful Commands"
echo "========================================="
echo ""
echo "Logs:"
echo "  kubectl -n nexusforge logs -l app=gateway -f"
echo "  kubectl -n nexusforge logs -l app=frontend -f"
echo "  kubectl -n nexusforge logs -l app=worker -f"
echo ""
echo "Evidence capture:"
echo "  ./scripts/k8s-evidence.sh"
echo ""
echo "Teardown:"
echo "  $KIND_CMD delete cluster --name nexusforge"
echo ""
echo "=== Kind deploy complete ==="
