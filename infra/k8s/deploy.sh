#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# deploy.sh — Deploy the Blackjack application to EKS
#
# Prerequisites:
#   - kubectl configured (aws eks update-kubeconfig --name blackjack-staging)
#   - AWS CLI with access to SSM Parameter Store
#   - Terraform already applied (EKS cluster exists)
#
# Usage:
#   ./deploy.sh                          # fetches secrets from SSM
#   DB_PASSWORD=xxx SECRET_KEY=yyy ./deploy.sh   # explicit secrets
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

NAMESPACE="blackjack"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔══════════════════════════════════════════════╗"
echo "║   Deploying Blackjack to EKS                ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Prerequisites check ──────────────────────────────────────────────────────
command -v kubectl >/dev/null 2>&1 || { echo "❌ kubectl not found. Install it first."; exit 1; }
command -v aws >/dev/null 2>&1    || { echo "❌ aws CLI not found. Install it first."; exit 1; }

# Verify cluster connectivity
if ! kubectl cluster-info >/dev/null 2>&1; then
  echo "❌ Cannot reach Kubernetes cluster. Run:"
   echo "   aws eks update-kubeconfig --name blackjack-staging --region ap-south-1"
  exit 1
fi

echo "✅ Connected to cluster: $(kubectl config current-context)"
echo ""

# ── Gather secrets ───────────────────────────────────────────────────────────
AWS_REGION="${AWS_REGION:-ap-south-1}"
APP_NAME="${APP_NAME:-blackjack}"
ENV="${ENVIRONMENT:-staging}"

if [ -z "${DB_PASSWORD:-}" ] || [ -z "${SECRET_KEY:-}" ]; then
  echo "🔐 Fetching secrets from SSM Parameter Store..."
  DB_PASSWORD=$(aws ssm get-parameter \
    --name "/${APP_NAME}/${ENV}/db_password" \
    --with-decryption \
    --query Parameter.Value \
    --output text \
    --region "$AWS_REGION")

  SECRET_KEY=$(aws ssm get-parameter \
    --name "/${APP_NAME}/${ENV}/secret_key" \
    --with-decryption \
    --query Parameter.Value \
    --output text \
    --region "$AWS_REGION")

  echo "   Secrets fetched from SSM."
else
  echo "🔐 Using secrets from environment variables."
fi

POSTGRES_USER="${POSTGRES_USER:-blackjack}"
POSTGRES_PASSWORD="${DB_PASSWORD}"
POSTGRES_DB="${POSTGRES_DB:-blackjack}"
DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}"

# ── Image tag resolution ─────────────────────────────────────────────────────
ECR_REPO="${ECR_REPO:-904233124111.dkr.ecr.ap-south-1.amazonaws.com/blackjack-application}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
echo "🏷️  ECR repo:  $ECR_REPO"
echo "🏷️  Image tag: $IMAGE_TAG"

# ── 1. Namespace ─────────────────────────────────────────────────────────────
echo ""
echo "📦 [1/6] Creating namespace..."
kubectl apply -f "$SCRIPT_DIR/namespace.yaml"

# ── 2. Secrets ───────────────────────────────────────────────────────────────
echo "🔑 [2/6] Creating Kubernetes secrets..."
kubectl -n "$NAMESPACE" create secret generic blackjack-secrets \
  --from-literal=POSTGRES_USER="$POSTGRES_USER" \
  --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --from-literal=POSTGRES_DB="$POSTGRES_DB" \
  --from-literal=DATABASE_URL="$DATABASE_URL" \
  --from-literal=SECRET_KEY="$SECRET_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

# ── 3. Network Policies ─────────────────────────────────────────────────────
echo "🛡️  [3/6] Applying network policies..."
kubectl apply -f "$SCRIPT_DIR/network-policy.yaml"

# ── 4. PostgreSQL ────────────────────────────────────────────────────────────
echo "🐘 [4/6] Deploying PostgreSQL..."
kubectl apply -f "$SCRIPT_DIR/postgres.yaml"
echo "   Waiting for PostgreSQL to be ready..."
kubectl -n "$NAMESPACE" rollout status statefulset/postgres --timeout=180s

# ── 5. Backend ───────────────────────────────────────────────────────────────
echo "⚙️  [5/6] Deploying backend..."
sed -e "s|ECR_REPO|${ECR_REPO}|g" -e "s|IMAGE_TAG|${IMAGE_TAG}|g" \
  "$SCRIPT_DIR/backend.yaml" | kubectl apply -f -
kubectl -n "$NAMESPACE" rollout status deployment/backend --timeout=120s

# ── 6. Frontend + NLB ────────────────────────────────────────────────────────
echo "🌐 [6/6] Deploying frontend (+ NLB provisioning)..."
sed -e "s|ECR_REPO|${ECR_REPO}|g" -e "s|IMAGE_TAG|${IMAGE_TAG}|g" \
  "$SCRIPT_DIR/frontend.yaml" | kubectl apply -f -
kubectl -n "$NAMESPACE" rollout status deployment/frontend --timeout=120s

# ── Wait for LoadBalancer URL ────────────────────────────────────────────────
echo ""
echo "⏳ Waiting for NLB external hostname..."
LB_HOST=""
for i in $(seq 1 30); do
  LB_HOST=$(kubectl -n "$NAMESPACE" get svc frontend \
    -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)
  if [ -n "$LB_HOST" ]; then
    break
  fi
  printf "."
  sleep 10
done
echo ""

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   Deployment Complete!                       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

if [ -n "$LB_HOST" ]; then
  echo "🎰 Application URL:  http://$LB_HOST"
  echo ""
  echo "   (NLB may take 2-3 minutes to become fully reachable)"
else
  echo "⚠️  NLB hostname not available yet. Check manually:"
  echo "   kubectl -n $NAMESPACE get svc frontend"
fi

echo ""
echo "Useful commands:"
echo "  kubectl -n $NAMESPACE get pods              # pod status"
echo "  kubectl -n $NAMESPACE logs deploy/backend   # backend logs"
echo "  kubectl -n $NAMESPACE logs deploy/frontend  # frontend logs"
echo "  kubectl -n $NAMESPACE get svc frontend      # NLB hostname"
echo ""
