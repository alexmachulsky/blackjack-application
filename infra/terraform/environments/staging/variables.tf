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

# ── EC2 ─────────────────────────────────────────────────────────────────────────
variable "key_name" {
  description = "Name of an existing EC2 Key Pair for SSH access"
  type        = string
}

variable "instance_type" {
  type    = string
  default = "t3.small"
}

variable "admin_cidr" {
  description = "Your IP CIDR for SSH access (e.g. 203.0.113.5/32)"
  type        = string
  default     = "0.0.0.0/0"
}

# ── RDS ─────────────────────────────────────────────────────────────────────────
variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "db_name" {
  type    = string
  default = "blackjack"
}

variable "db_username" {
  type    = string
  default = "blackjack"
}

# ── Images ──────────────────────────────────────────────────────────────────────
variable "ghcr_owner" {
  description = "GitHub owner of GHCR packages (e.g. alexmachulsky)"
  type        = string
  default     = "alexmachulsky"
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}
