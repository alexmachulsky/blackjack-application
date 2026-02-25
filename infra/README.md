# Infrastructure — AWS EKS (Terraform + Kubernetes)

## Architecture

```
Internet
    │
    ▼
  NLB (port 80)                         ← auto-created by K8s Service
    │
    ▼
  EKS Cluster (blackjack-staging)
  ┌──────────────────────────────────┐
  │  1× t3.small node               │
  │  ├── frontend  (nginx, 1 pod)   │
  │  ├── backend   (FastAPI, 1 pod) │
  │  └── postgres  (StatefulSet)    │
  │       └── 5 GB EBS gp3 PVC     │
  └──────────────────────────────────┘
```

## Directory structure

```
infra/
├── docker-compose.aws.yml          # Legacy: EC2-based deploy override
├── k8s/                            # Kubernetes manifests
│   ├── namespace.yaml
│   ├── postgres.yaml               # StatefulSet + headless Service + gp3 StorageClass
│   ├── backend.yaml                # Deployment + ClusterIP Service
│   ├── frontend.yaml               # Deployment + LoadBalancer Service (NLB)
│   └── deploy.sh                   # One-command deployment script
└── terraform/
    ├── modules/
    │   ├── vpc/                    # VPC, subnets (with EKS discovery tags), IGW
    │   ├── eks/                    # EKS cluster, node group, OIDC, EBS CSI driver
    │   ├── alb/                    # (legacy — kept for reference)
    │   ├── ec2/                    # (legacy — kept for reference)
    │   ├── rds/                    # (legacy — kept for reference)
    │   └── security_groups/        # (legacy — kept for reference)
    └── environments/
        └── staging/
            ├── backend.tf          # S3 remote state + provider config
            ├── main.tf             # Root module: VPC → EKS
            ├── variables.tf
            ├── secrets.tf          # Sensitive vars (db_password, secret_key)
            ├── outputs.tf
            └── terraform.tfvars.example
```

## Cost estimate (~730 hrs/month, ap-south-1)

| Resource | Monthly Cost |
|----------|-------------|
| EKS control plane | $73.00 |
| EC2 t3.small (1 node) | ~$15 |
| NLB | ~$18 |
| EBS gp3 5 GB (PostgreSQL) | ~$0.40 |
| **Total** | **~$107/month** |

> **Cost-saving tip**: Stop the EKS node group when not in use:
> ```bash
> aws eks update-nodegroup-config \
>   --cluster-name blackjack-staging \
>   --nodegroup-name blackjack-staging-nodes \
>   --scaling-config minSize=0,maxSize=2,desiredSize=0 \
>   --region ap-south-1
> ```
> This reduces cost to ~$73/month (control plane only). Scale back up by setting desiredSize=1.

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Terraform | >= 1.7 | `brew install terraform` |
| AWS CLI | >= 2.x | `brew install awscli` |
| kubectl | >= 1.28 | `brew install kubectl` |
| AWS account | IAM user with AdministratorAccess | — |

## One-time bootstrap (remote state)

```bash
# 1. Create S3 bucket for Terraform state
aws s3api create-bucket --bucket blackjack-tf-state --region ap-south-1 \
  --create-bucket-configuration LocationConstraint=ap-south-1

aws s3api put-bucket-versioning \
  --bucket blackjack-tf-state \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket blackjack-tf-state \
  --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# 2. Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-south-1
```

## Deploying

### Step 1 — Provision infrastructure (~15 minutes)

```bash
cd infra/terraform/environments/staging

# Copy and edit the example vars file
cp terraform.tfvars.example terraform.tfvars

# Set secrets as environment variables (never put in tfvars file)
export TF_VAR_db_password="$(openssl rand -base64 24)"
export TF_VAR_app_secret_key="$(openssl rand -hex 32)"

# Provision EKS cluster + VPC
terraform init
terraform plan -out=staging.tfplan
terraform apply staging.tfplan
```

### Step 2 — Configure kubectl

```bash
aws eks update-kubeconfig --name blackjack-staging --region ap-south-1

# Verify connectivity
kubectl get nodes
```

### Step 3 — Deploy application (~2 minutes)

```bash
cd infra/k8s
./deploy.sh
```

The script will:
1. Create the `blackjack` namespace
2. Fetch secrets from SSM Parameter Store and create K8s Secrets
3. Deploy PostgreSQL (StatefulSet with 5 GB EBS volume)
4. Deploy backend (FastAPI) with init container waiting for PostgreSQL
5. Deploy frontend (Nginx) with NLB
6. Print the application URL

### Updating the application

After pushing new images via CI/CD:

```bash
# Update backend image
kubectl -n blackjack set image deployment/backend \
  backend=ghcr.io/alexmachulsky/blackjack-backend:sha-abc1234

# Update frontend image
kubectl -n blackjack set image deployment/frontend \
  frontend=ghcr.io/alexmachulsky/blackjack-frontend:sha-abc1234
```

## Tearing down

```bash
# Delete K8s resources first (removes NLB)
kubectl delete namespace blackjack

# Then destroy Terraform resources
cd infra/terraform/environments/staging
terraform destroy
```

This removes all resources **except** the S3 state bucket and DynamoDB lock table (managed manually).
