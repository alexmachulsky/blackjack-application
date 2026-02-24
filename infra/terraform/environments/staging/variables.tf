variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Application name (used in resource names and tags)"
  type        = string
  default     = "blackjack"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "staging"
}

variable "availability_zones" {
  description = "AZs to deploy subnets into (must be in var.aws_region)"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# ── EKS ─────────────────────────────────────────────────────────────────────────
variable "kubernetes_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.31"
}

variable "node_instance_type" {
  description = "EC2 instance type for EKS worker nodes"
  type        = string
  default     = "t3.small"
}

# ── Database (runs in-cluster as StatefulSet) ────────────────────────────────
variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "blackjack"
}

variable "db_username" {
  description = "PostgreSQL username"
  type        = string
  default     = "blackjack"
}
