# ──────────────────────────────────────────────────────────────────────────────
# Security Groups
#
#  alb-sg  — internet-facing load balancer (HTTP/HTTPS from world)
#  ec2-sg  — app server (HTTP from ALB, SSH from admin CIDR)
#  rds-sg  — database (Postgres from EC2 only)
# ──────────────────────────────────────────────────────────────────────────────

# ── ALB ───────────────────────────────────────────────────────────────────────
resource "aws_security_group" "alb" {
  name        = "${var.app_name}-${var.environment}-alb-sg"
  description = "Allow HTTP/HTTPS from the internet to the ALB"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.app_name}-${var.environment}-alb-sg" })
}

# ── EC2 ───────────────────────────────────────────────────────────────────────
resource "aws_security_group" "ec2" {
  name        = "${var.app_name}-${var.environment}-ec2-sg"
  description = "Allow HTTP from ALB and SSH from admin"
  vpc_id      = var.vpc_id

  # Traffic from the ALB only
  ingress {
    description     = "HTTP from ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # SSH for initial setup and emergency access
  ingress {
    description = "SSH from admin"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.app_name}-${var.environment}-ec2-sg" })
}

# ── RDS ───────────────────────────────────────────────────────────────────────
resource "aws_security_group" "rds" {
  name        = "${var.app_name}-${var.environment}-rds-sg"
  description = "Allow Postgres from EC2 only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Postgres from EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.app_name}-${var.environment}-rds-sg" })
}
