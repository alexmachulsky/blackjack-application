#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# deploy.sh — Deploy blackjack to Minikube
#
# Prerequisites (one-time, per fresh cluster):
#   1. minikube start --driver=docker --cpus=2 --memory=4g
#   2. minikube addons enable metrics-server
#   3. kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/controller.yaml
#   4. Generate infra/k8s/ghcr-pull-secret.yaml — see infra/README.md
#
# Usage (day-to-day):
#   export DB_PASSWORD=yourpassword
#   export SECRET_KEY=your-secret-key-minimum-32-characters
#   export POSTGRES_USER=blackjack          # optional, default: blackjack
#   export POSTGRES_PASSWORD=yourpassword   # optional, defaults to DB_PASSWORD
#   export POSTGRES_DB=blackjack            # optional, default: blackjack
#   ./infra/k8s/deploy.sh
#
# Access the app at: http://$(minikube ip):30080
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_NAME="${APP_NAME:-blackjack}"
NAMESPACE="${NAMESPACE:-blackjack}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Preflight checks ──────────────────────────────────────────────────────────
info "Checking prerequisites..."

if ! command -v minikube &>/dev/null; then
  error "minikube not found. Install it from https://minikube.sigs.k8s.io/docs/start/"
  exit 1
fi

if ! minikube status --format='{{.Host}}' 2>/dev/null | grep -q "Running"; then
  error "Minikube is not running. Start it with:"
  error "  minikube start --driver=docker --cpus=2 --memory=4g"
  exit 1
fi

if ! command -v kubectl &>/dev/null; then
  error "kubectl not found. You can use: minikube kubectl --"
  exit 1
fi

info "Minikube is running. Context: $(kubectl config current-context)"

# ── Sealed Secrets controller check ──────────────────────────────────────────
if ! kubectl get deployment sealed-secrets-controller -n kube-system &>/dev/null; then
  error "sealed-secrets controller not found in kube-system."
  error "Install it with:"
  error "  kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/controller.yaml"
  error "Then wait for it to be ready and re-run this script."
  exit 1
fi

if ! kubectl rollout status deployment/sealed-secrets-controller \
     -n kube-system --timeout=60s &>/dev/null; then
  error "sealed-secrets controller is not Ready (may still be starting)."
  error "Wait with: kubectl rollout status deployment/sealed-secrets-controller -n kube-system"
  exit 1
fi

if [[ ! -f "${SCRIPT_DIR}/ghcr-pull-secret.yaml" ]]; then
  error "infra/k8s/ghcr-pull-secret.yaml not found."
  error "Generate it with kubeseal — see infra/README.md for instructions."
  exit 1
fi

# ── Validate required secrets ─────────────────────────────────────────────────
if [[ -z "${DB_PASSWORD:-}" ]]; then
  error "DB_PASSWORD is required. Set it with: export DB_PASSWORD=yourpassword"
  exit 1
fi
if [[ -z "${SECRET_KEY:-}" ]]; then
  error "SECRET_KEY is required (min 32 chars). Set it with: export SECRET_KEY=..."
  exit 1
fi

POSTGRES_USER="${POSTGRES_USER:-blackjack}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-${DB_PASSWORD}}"
POSTGRES_DB="${POSTGRES_DB:-blackjack}"
DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}"

# ── Namespace ─────────────────────────────────────────────────────────────────
info "Creating namespace..."
kubectl apply -f "${SCRIPT_DIR}/namespace.yaml"

# ── Secrets ───────────────────────────────────────────────────────────────────
info "Creating Kubernetes secrets..."
kubectl create secret generic blackjack-secrets \
  --namespace="${NAMESPACE}" \
  --from-literal=DATABASE_URL="${DATABASE_URL}" \
  --from-literal=SECRET_KEY="${SECRET_KEY}" \
  --from-literal=POSTGRES_USER="${POSTGRES_USER}" \
  --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
  --from-literal=POSTGRES_DB="${POSTGRES_DB}" \
  --dry-run=client -o yaml | kubectl apply -f -

# ── GHCR pull secret ──────────────────────────────────────────────────────────
info "Applying GHCR image pull secret..."
kubectl apply -f "${SCRIPT_DIR}/ghcr-pull-secret.yaml"

info "Waiting for pull secret to be unsealed by controller..."
if ! kubectl wait secret/ghcr-pull-secret \
     -n "${NAMESPACE}" --for=jsonpath='{.type}'=kubernetes.io/dockerconfigjson \
     --timeout=30s 2>/dev/null; then
  warn "Pull secret not yet visible after 30s — proceeding, but watch for ImagePullBackOff"
fi

# ── Network policies ──────────────────────────────────────────────────────────
info "Applying network policies..."
kubectl apply -f "${SCRIPT_DIR}/network-policy.yaml"

# ── PostgreSQL ────────────────────────────────────────────────────────────────
info "Deploying PostgreSQL..."
kubectl apply -f "${SCRIPT_DIR}/postgres.yaml"

info "Waiting for PostgreSQL to be ready..."
kubectl rollout status statefulset/postgres -n "${NAMESPACE}" --timeout=120s

# ── Backend ───────────────────────────────────────────────────────────────────
info "Deploying backend..."
kubectl apply -f "${SCRIPT_DIR}/backend.yaml"

info "Waiting for backend to be ready..."
kubectl rollout status deployment/backend -n "${NAMESPACE}" --timeout=120s

# ── Frontend ──────────────────────────────────────────────────────────────────
info "Deploying frontend..."
kubectl apply -f "${SCRIPT_DIR}/frontend.yaml"

info "Waiting for frontend to be ready..."
kubectl rollout status deployment/frontend -n "${NAMESPACE}" --timeout=120s

# ── Optional: HPA + PDB ───────────────────────────────────────────────────────
if minikube addons list | grep -q "metrics-server: enabled"; then
  info "Applying HPA (metrics-server detected)..."
  kubectl apply -f "${SCRIPT_DIR}/hpa.yaml"
else
  warn "metrics-server not enabled — skipping HPA. Enable with: minikube addons enable metrics-server"
fi

kubectl apply -f "${SCRIPT_DIR}/pdb.yaml"

# ── Done ──────────────────────────────────────────────────────────────────────
MINIKUBE_IP=$(minikube ip)
echo ""
info "Deployment complete!"
echo -e "  ${GREEN}App URL:${NC}    http://${MINIKUBE_IP}:30080"
echo -e "  ${GREEN}Health:${NC}     http://${MINIKUBE_IP}:30080/health"
echo -e "  ${GREEN}API docs:${NC}   http://${MINIKUBE_IP}:30080/docs"
echo ""
info "Useful commands:"
echo "  kubectl get pods -n ${NAMESPACE}"
echo "  kubectl logs -n ${NAMESPACE} -l app=backend -f"
echo "  kubectl logs -n ${NAMESPACE} -l app=postgres -f"
