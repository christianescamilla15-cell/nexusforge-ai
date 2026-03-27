#!/bin/bash
# NexusForge AI — Local Kubernetes Deployment
# Requires: kubectl, docker (or minikube/kind)
# Usage: ./scripts/k8s-local-deploy.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== NexusForge AI — K8s Local Deploy ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# Detect cluster type and configure image loading
CLUSTER_TYPE="docker-desktop"
if command -v minikube &>/dev/null && minikube status &>/dev/null 2>&1; then
    CLUSTER_TYPE="minikube"
    echo "Detected minikube cluster"
    eval $(minikube docker-env)
elif command -v kind &>/dev/null && kind get clusters 2>/dev/null | grep -q .; then
    CLUSTER_TYPE="kind"
    echo "Detected kind cluster"
fi

# 1. Build Docker images
echo ""
echo "[1/6] Building Docker images..."
echo "Building backend image..."
docker build -t nexusforge-backend:latest -f backend/Dockerfile backend/

echo "Building frontend image..."
docker build -t nexusforge-frontend:latest -f frontend/Dockerfile frontend/ 2>/dev/null || echo "WARNING: Frontend Dockerfile not found, skipping..."

# For kind, load images into the cluster
if [ "$CLUSTER_TYPE" = "kind" ]; then
    CLUSTER_NAME=$(kind get clusters 2>/dev/null | head -1)
    echo "Loading images into kind cluster '$CLUSTER_NAME'..."
    kind load docker-image nexusforge-backend:latest --name "$CLUSTER_NAME"
    kind load docker-image nexusforge-frontend:latest --name "$CLUSTER_NAME" 2>/dev/null || true
fi

# 2. Create namespace
echo ""
echo "[2/6] Creating namespace..."
kubectl apply -f infrastructure/k8s/base/namespace.yml

# 3. Apply configs and secrets
echo ""
echo "[3/6] Applying configs and secrets..."
kubectl apply -f infrastructure/k8s/base/configmap.yml
kubectl apply -f infrastructure/k8s/base/secrets.yml

# 4. Deploy stateful services (Redis)
echo ""
echo "[4/6] Deploying Redis..."
kubectl apply -f infrastructure/k8s/base/redis-statefulset.yml

# 5. Deploy application services
echo ""
echo "[5/6] Deploying application services..."
echo "Deploying backend gateway..."
kubectl apply -f infrastructure/k8s/base/gateway-deployment.yml
kubectl apply -f infrastructure/k8s/base/gateway-service.yml

echo "Deploying workers..."
kubectl apply -f infrastructure/k8s/base/worker-deployment.yml

echo "Deploying frontend..."
kubectl apply -f infrastructure/k8s/base/frontend-deployment.yml
kubectl apply -f infrastructure/k8s/base/frontend-service.yml

# Skip HPAs for local — they require metrics-server
echo "Skipping HPAs (not needed for local development)"

# 6. Wait for pods
echo ""
echo "[6/6] Waiting for pods to be ready..."
kubectl -n nexusforge wait --for=condition=ready pod -l app=redis --timeout=90s 2>/dev/null || echo "WARNING: Redis still starting..."
kubectl -n nexusforge wait --for=condition=ready pod -l app=gateway --timeout=120s 2>/dev/null || echo "WARNING: Gateway still starting..."
kubectl -n nexusforge wait --for=condition=ready pod -l app=frontend --timeout=90s 2>/dev/null || echo "WARNING: Frontend still starting..."

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
echo "       Access (port-forward)"
echo "========================================="
echo ""
echo "Backend API:"
echo "  kubectl -n nexusforge port-forward svc/gateway 8000:8000"
echo "  -> http://localhost:8000"
echo ""
echo "Frontend:"
echo "  kubectl -n nexusforge port-forward svc/frontend 3000:80"
echo "  -> http://localhost:3000"
echo ""
echo "Redis:"
echo "  kubectl -n nexusforge port-forward svc/redis 6379:6379"
echo ""
echo "Health check:"
echo "  curl http://localhost:8000/health"
echo ""
echo "Teardown:"
echo "  ./scripts/k8s-teardown.sh"
echo ""
echo "=== Deploy complete ==="
