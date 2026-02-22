# ──────────────────────────────────────────────────────────────────────────────
# RDS — PostgreSQL 15 in private subnets
#
# Password is fetched from SSM Parameter Store (SecureString) so it never
# appears in Terraform plan output or state files unencrypted.
# ──────────────────────────────────────────────────────────────────────────────

data "aws_ssm_parameter" "db_password" {
  name            = var.db_password_ssm_path
  with_decryption = true
}

resource "aws_db_subnet_group" "this" {
  name        = "${var.app_name}-${var.environment}-rds-subnet-group"
  description = "Private subnets for ${var.app_name} ${var.environment} RDS"
  subnet_ids  = var.private_subnet_ids

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-rds-subnet-group"
  })
}

resource "aws_db_instance" "this" {
  identifier = "${var.app_name}-${var.environment}-postgres"

  # Engine
  engine         = "postgres"
  engine_version = var.postgres_version
  instance_class = var.db_instance_class

  # Storage
  allocated_storage     = var.allocated_storage
  max_allocated_storage = 100            # autoscaling upper bound
  storage_type          = "gp3"
  storage_encrypted     = true

  # Database
  db_name  = var.db_name
  username = var.db_username
  password = data.aws_ssm_parameter.db_password.value

  # Network
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [var.rds_sg_id]
  publicly_accessible    = false

  # Maintenance / backup
  backup_retention_period   = 7
  backup_window             = "03:00-04:00"
  maintenance_window        = "Mon:04:00-Mon:05:00"
  auto_minor_version_upgrade = true

  # Staging: skip snapshot on destroy so `terraform destroy` is fast
  skip_final_snapshot = true
  deletion_protection = false

  # Performance Insights (free tier for db.t3.micro)
  performance_insights_enabled = false

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-postgres"
  })
}
