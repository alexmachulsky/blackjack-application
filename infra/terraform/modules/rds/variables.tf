variable "app_name" { type = string }
variable "environment" { type = string }

variable "private_subnet_ids" {
  description = "Private subnet IDs for the RDS subnet group"
  type        = list(string)
}

variable "rds_sg_id" {
  description = "Security group ID to attach to the RDS instance"
  type        = string
}

variable "db_name" {
  description = "Name of the initial database"
  type        = string
  default     = "blackjack"
}

variable "db_username" {
  description = "Master DB username"
  type        = string
  default     = "blackjack"
}

variable "db_password_ssm_path" {
  description = "SSM Parameter path for the DB master password (SecureString)"
  type        = string
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "postgres_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15"
}

variable "allocated_storage" {
  description = "Initial storage in GiB"
  type        = number
  default     = 20
}

variable "tags" {
  type    = map(string)
  default = {}
}
