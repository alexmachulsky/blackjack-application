variable "app_name" { type = string }
variable "environment" { type = string }

variable "subnet_id" {
  description = "Public subnet ID to launch the instance in"
  type        = string
}

variable "ec2_sg_id" {
  description = "Security group ID for the EC2 instance"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "key_name" {
  description = "Name of an existing EC2 Key Pair for SSH access"
  type        = string
}

variable "iam_instance_profile" {
  description = "IAM instance profile name to attach"
  type        = string
}

# ── Values injected into user_data ───────────────────────────────────────────
variable "db_host" { type = string }
variable "db_port" { type = string }
variable "db_name" { type = string }
variable "db_username" { type = string }

variable "db_password_ssm_path" {
  description = "SSM path from which user_data fetches the DB password at boot"
  type        = string
}

variable "secret_key_ssm_path" {
  description = "SSM path from which user_data fetches the JWT secret key at boot"
  type        = string
}

variable "ghcr_owner" {
  description = "GitHub username / org that owns the GHCR packages"
  type        = string
}

variable "backend_image" {
  description = "Full GHCR image reference for the backend (e.g. ghcr.io/org/blackjack-backend)"
  type        = string
}

variable "frontend_image" {
  description = "Full GHCR image reference for the frontend"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "aws_region" {
  description = "AWS region (used by user_data when calling SSM)"
  type        = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
