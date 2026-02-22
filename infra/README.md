# Infrastructure — AWS (Terraform)

## Architecture

```
Internet
    │
    ▼
  ALB (port 80)                    ← public subnets, us-east-1a/1b
    │
    ▼
  EC2 t3.small                     ← public subnet, Amazon Linux 2023
  ┌─────────────────────────────┐
  │  Docker Compose             │
  │  ├─ nginx (frontend :80)    │
  │  └─ FastAPI (backend :8000) │
  └─────────────────────────────┘
    │
    ▼
  RDS PostgreSQL db.t3.micro       ← private subnets
```

## Module structure

```
infra/
├── docker-compose.aws.yml         # Compose override: removes postgres container, uses RDS
└── terraform/
    ├── modules/
    │   ├── vpc/                   # VPC, subnets, IGW, route tables
    │   ├── security_groups/       # ALB, EC2, RDS security groups
    │   ├── rds/                   # PostgreSQL 15 on db.t3.micro
    │   ├── ec2/                   # App server + user_data bootstrap
    │   └── alb/                   # Internet-facing ALB + target group
    └── environments/
        └── staging/
            ├── backend.tf         # S3 remote state + DynamoDB lock
            ├── main.tf            # Root module — wires everything together
            ├── variables.tf
            ├── secrets.tf         # Sensitive vars (db_password, secret_key)
            ├── outputs.tf
            └── terraform.tfvars.example
```

## Prerequisites

| Tool         | Version  |
|--------------|----------|
| Terraform    | >= 1.7   |
| AWS CLI      | >= 2.x   |
| AWS account  | IAM user with AdministratorAccess (or scoped policy) |

## One-time bootstrap (remote state)

```bash
# 1. Create S3 bucket for Terraform state
aws s3api create-bucket --bucket blackjack-tf-state --region us-east-1

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
  --region us-east-1
```

## Deploying staging

```bash
cd infra/terraform/environments/staging

# Copy and edit the example vars file
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — set key_name, admin_cidr, etc.

# Set secrets as environment variables (never put in tfvars file)
export TF_VAR_db_password="$(openssl rand -base64 24)"
export TF_VAR_app_secret_key="$(openssl rand -hex 32)"

# Initialise, plan, apply
terraform init
terraform plan -out=staging.tfplan
terraform apply staging.tfplan
```

After apply, Terraform prints:

```
alb_dns_name   = "http://blackjack-staging-alb-<id>.us-east-1.elb.amazonaws.com"
ec2_public_ip  = "x.x.x.x"
rds_endpoint   = "blackjack-staging-postgres.<id>.us-east-1.rds.amazonaws.com:5432"
```

Open `alb_dns_name` in your browser — the app will be live once the EC2 user_data bootstrap completes (~2 min).

## GitHub Actions integration (CI Stage 7)

Add these secrets to `Settings → Environments → staging`:

| Secret           | Value                                     |
|------------------|-------------------------------------------|
| `DEPLOY_HOST`    | EC2 public IP from `terraform output`     |
| `DEPLOY_USER`    | `ec2-user`                                |
| `DEPLOY_SSH_KEY` | Private key matching `var.key_name`       |

## Tearing down

```bash
terraform destroy
```

This removes all resources **except** the S3 state bucket and DynamoDB lock table (managed manually).

## Cost estimate (staging, us-east-1, ~730 hrs/month)

| Resource           | Approx monthly cost |
|--------------------|---------------------|
| EC2 t3.small       | ~$15                |
| RDS db.t3.micro    | ~$14                |
| ALB                | ~$18                |
| **Total**          | **~$47/month**      |

> Stop the EC2 instance when not in active use to reduce costs.
