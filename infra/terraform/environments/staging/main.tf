# ──────────────────────────────────────────────────────────────────────────────
# Staging environment — EKS deployment
#
# Wires together: VPC → EKS (cluster + node group + EBS CSI)
# PostgreSQL runs as a K8s StatefulSet (not RDS) to minimize cost.
# ──────────────────────────────────────────────────────────────────────────────

locals {
  cluster_name = "${var.app_name}-${var.environment}"
  ssm_prefix   = "/${var.app_name}/${var.environment}"
}

# ── SSM Parameter Store — secrets written by Terraform, read by deploy.sh ────
resource "aws_ssm_parameter" "db_password" {
  name        = "${local.ssm_prefix}/db_password"
  description = "PostgreSQL password for ${var.app_name} ${var.environment}"
  type        = "SecureString"
  value       = var.db_password

  tags = { Name = "${var.app_name}-${var.environment}-db-password" }
}

resource "aws_ssm_parameter" "secret_key" {
  name        = "${local.ssm_prefix}/secret_key"
  description = "JWT secret key for ${var.app_name} ${var.environment}"
  type        = "SecureString"
  value       = var.app_secret_key

  tags = { Name = "${var.app_name}-${var.environment}-secret-key" }
}

# ── VPC ───────────────────────────────────────────────────────────────────────
module "vpc" {
  source = "../../modules/vpc"

  app_name             = var.app_name
  environment          = var.environment
  cluster_name         = local.cluster_name
  vpc_cidr             = "10.0.0.0/16"
  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.3.0/24", "10.0.4.0/24"]
  availability_zones   = var.availability_zones
}

# ── EKS ───────────────────────────────────────────────────────────────────────
module "eks" {
  source = "../../modules/eks"

  cluster_name       = local.cluster_name
  kubernetes_version = var.kubernetes_version

  # Cluster control plane spans both public subnets
  subnet_ids = module.vpc.public_subnet_ids

  # Nodes in public subnets — avoids NAT gateway cost (~$32/month savings)
  node_subnet_ids    = module.vpc.public_subnet_ids
  node_instance_type = var.node_instance_type
  node_desired_size  = 1
  node_min_size      = 1
  node_max_size      = 2
  node_disk_size     = 20
}
