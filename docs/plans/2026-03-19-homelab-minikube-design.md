# Home Lab Minikube Setup — Design

**Date:** 2026-03-19
**Status:** Approved

## Goal

Clean up the project to be a proper home lab setup: Minikube on-prem, private GHCR images pulled securely via Sealed Secrets, no cloud dependencies, no Terraform.

## Context

The project was recently migrated from AWS EKS + Terraform to Minikube + GHCR. The K8s manifests and CI pipeline are already Minikube-compatible, but several gaps remain:

- GHCR packages are public — no auth on image pulls
- No `imagePullSecrets` in pod specs
- `infra/README.md` still fully documents the old AWS EKS + Terraform setup
- Stale comments reference EBS, NLB, and AWS-specific behaviour

## Decisions

### Secret management: Sealed Secrets

Chosen over alternatives because:
- **vs. PAT in env var at deploy time:** Sealed Secrets is more GitOps-idiomatic — the encrypted secret is versioned in the repo, deploy needs no runtime credentials
- **vs. Minikube docker-env credential sharing:** Session-scoped, not standard K8s practice
- **vs. External Secrets Operator:** Overkill, requires external secret backend

The private key loss concern (relevant if Minikube is wiped with `minikube delete`) does not apply here — the cluster is long-lived and only stopped/started, never deleted.

### App secrets (DB_PASSWORD, SECRET_KEY): unchanged

These remain created imperatively by `deploy.sh` from exported env vars. Only the GHCR pull secret is sealed — it's the only secret that benefits from being committed to the repo.

## Architecture

```
Developer machine
│
├── minikube start
├── kubectl apply -f infra/k8s/   (deploy.sh)
│   ├── namespace.yaml
│   ├── network-policy.yaml
│   ├── ghcr-pull-secret.yaml     ← NEW: SealedSecret (decrypted by controller)
│   ├── postgres.yaml
│   ├── backend.yaml              ← imagePullSecrets added
│   ├── frontend.yaml             ← imagePullSecrets added
│   ├── hpa.yaml
│   └── pdb.yaml
│
└── Minikube kubelet pulls images from ghcr.io (private)
    └── authenticates via ghcr-pull-secret (K8s docker-registry secret)

CI (GitHub Actions)
└── Pushes backend + frontend images to ghcr.io (private)
    └── Uses ${{ secrets.GITHUB_TOKEN }} (unchanged)
```

## Changes

### 1. `infra/k8s/ghcr-pull-secret.yaml` — NEW FILE

A `SealedSecret` containing the GHCR PAT (read:packages scope). Generated once by the operator via:

```bash
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=alexmachulsky \
  --docker-password=<PAT> \
  --namespace=blackjack \
  --dry-run=client -o yaml \
  | kubeseal -o yaml > infra/k8s/ghcr-pull-secret.yaml
```

The file is committed to the repo. The raw PAT is never stored anywhere.

### 2. `infra/k8s/backend.yaml` + `infra/k8s/frontend.yaml`

Add `imagePullSecrets` to both pod specs:

```yaml
spec:
  template:
    spec:
      imagePullSecrets:
        - name: ghcr-pull-secret
```

### 3. `infra/k8s/deploy.sh`

- Add preflight check: verify sealed-secrets controller is running; print install command and exit if not
- Apply `ghcr-pull-secret.yaml` immediately after namespace creation (before any workload manifests)
- Remove any registry login / GITHUB_TOKEN references from deploy comments

### 4. `infra/README.md` — full rewrite

Replace the AWS EKS + Terraform documentation with a Minikube guide:

- Architecture diagram (Minikube-based)
- Prerequisites: `minikube`, `kubectl`, `kubeseal`, `make`
- One-time cluster setup (start Minikube, install sealed-secrets controller, seal the GHCR PAT, set GHCR packages to private in GitHub settings)
- Day-to-day deploy flow
- Useful kubectl commands

### 5. Stale comment cleanup

| File | Current comment | Fix |
|---|---|---|
| `frontend.yaml` | `# LoadBalancer Service — creates an AWS NLB automatically` | Remove |
| `postgres.yaml` | `# PGDATA must be a subdirectory of the mount (EBS has a lost+found dir)` | Update to reference Minikube hostPath |

## One-time operator steps (not automated)

These must be done manually by the operator once per fresh Minikube cluster:

1. Start Minikube: `minikube start --driver=docker --cpus=2 --memory=4g`
2. Enable metrics-server: `minikube addons enable metrics-server`
3. Install sealed-secrets controller: `kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/controller.yaml`
4. Install kubeseal CLI: `brew install kubeseal`
5. Create a GitHub PAT with `read:packages` scope
6. Run the `kubeseal` command above to generate `ghcr-pull-secret.yaml` and commit it
7. Set GHCR packages to **private** in GitHub → Packages settings

After these steps, `deploy.sh` handles everything for all future deploys.
