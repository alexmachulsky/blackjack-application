# Infrastructure — Minikube (Home Lab)

## Architecture

```
Internet (local network)
    │
    ▼
  http://$(minikube ip):30080          ← NodePort 30080
    │
    ▼
  Minikube cluster (single node)
  ┌──────────────────────────────────┐
  │  frontend  (nginx, 1 pod)        │  ← serves React SPA + proxies API
  │  backend   (FastAPI, 1 pod)      │  ← ClusterIP only
  │  postgres  (StatefulSet, 1 pod)  │  ← hostPath PVC via standard-retain
  └──────────────────────────────────┘
       ↑ images pulled from ghcr.io (private)
       ↑ authenticated via ghcr-pull-secret (SealedSecret)
```

Images are built and pushed to private GHCR by CI (GitHub Actions) on every merge to main.
The sealed-secrets controller decrypts the committed SealedSecret at deploy time.

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| `minikube` | Local K8s cluster | https://minikube.sigs.k8s.io/docs/start/ |
| `kubectl` | K8s CLI | `brew install kubectl` |
| `kubeseal` | Encrypt secrets for Sealed Secrets | `brew install kubeseal` |
| `make` | Dev convenience commands | pre-installed on macOS/Linux |

## One-time cluster setup

Run these once per fresh Minikube cluster. The cluster survives `minikube stop`/`start` — only `minikube delete` requires repeating these steps.

### 1. Start Minikube

```bash
minikube start --driver=docker --cpus=2 --memory=4g
minikube addons enable metrics-server
```

### 2. Install the sealed-secrets controller

```bash
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/controller.yaml
# Wait for it to be ready
kubectl rollout status deployment/sealed-secrets-controller -n kube-system --timeout=60s
```

### 3. Generate the GHCR pull secret

Create a GitHub Personal Access Token with `read:packages` scope at https://github.com/settings/tokens.

Then create the namespace and seal the secret:

```bash
kubectl apply -f infra/k8s/namespace.yaml

kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=alexmachulsky \
  --docker-password=<YOUR_PAT> \
  --namespace=blackjack \
  --dry-run=client -o yaml \
  | kubeseal -o yaml > infra/k8s/ghcr-pull-secret.yaml

git add infra/k8s/ghcr-pull-secret.yaml
git commit -m "feat: add sealed GHCR pull secret"
git push
```

The PAT is encrypted inside the file — it is safe to commit.

### 4. Set GHCR packages to private

In GitHub: Profile → Packages → select `blackjack-application/backend` → Package settings → Change visibility → Private. Repeat for `frontend`.

## Deploying

```bash
export DB_PASSWORD=yourpassword
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

./infra/k8s/deploy.sh
```

The script will:
1. Check Minikube is running and the sealed-secrets controller is ready
2. Create the `blackjack` namespace and app secrets
3. Apply and unseal the GHCR pull secret
4. Deploy PostgreSQL, backend, frontend
5. Apply HPA (if metrics-server is enabled) and PDB

Access the app: `open http://$(minikube ip):30080`

## Day-to-day operations

```bash
# Re-deploy after CI pushes a new image
git pull origin deploy/staging   # get updated image tags from CI
./infra/k8s/deploy.sh

# Watch pods
kubectl get pods -n blackjack -w

# Backend logs
kubectl logs -n blackjack -l app=backend -f

# Postgres logs
kubectl logs -n blackjack -l app=postgres -f

# Stop the cluster (state is preserved)
minikube stop

# Start the cluster again
minikube start
```

## Directory structure

```
infra/
├── k8s/
│   ├── namespace.yaml          # blackjack namespace
│   ├── network-policy.yaml     # default-deny + allow rules
│   ├── ghcr-pull-secret.yaml   # SealedSecret for GHCR pull auth (encrypted PAT)
│   ├── postgres.yaml           # StatefulSet + hostPath PVC + headless Service
│   ├── backend.yaml            # Deployment + ClusterIP Service
│   ├── frontend.yaml           # Deployment + NodePort 30080
│   ├── hpa.yaml                # HorizontalPodAutoscaler (requires metrics-server)
│   ├── pdb.yaml                # PodDisruptionBudget
│   └── deploy.sh               # One-command deploy script
└── README.md                   # This file
```
