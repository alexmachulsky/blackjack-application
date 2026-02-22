# ──────────────────────────────────────────────────────────────────────────────
# Staging environment — root module
#
# Wires together: VPC → Security Groups → RDS → EC2 → ALB
# ──────────────────────────────────────────────────────────────────────────────

locals {
  ssm_prefix     = "/${var.app_name}/${var.environment}"
  backend_image  = "ghcr.io/${var.ghcr_owner}/${var.app_name}-backend"
  frontend_image = "ghcr.io/${var.ghcr_owner}/${var.app_name}-frontend"
}

# ── SSM Parameter Store — secrets written by Terraform, read by EC2 at boot ───
resource "aws_ssm_parameter" "db_password" {
  name        = "${local.ssm_prefix}/db_password"
  description = "RDS master password for ${var.app_name} ${var.environment}"
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

  app_name           = var.app_name
  environment        = var.environment
  vpc_cidr           = "10.0.0.0/16"
  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.3.0/24", "10.0.4.0/24"]
  availability_zones = var.availability_zones
}

# ── Security Groups ───────────────────────────────────────────────────────────
module "security_groups" {
  source = "../../modules/security_groups"

  app_name    = var.app_name
  environment = var.environment
  vpc_id      = module.vpc.vpc_id
  admin_cidr  = var.admin_cidr
}

# ── IAM role for EC2 (SSM agent + read own SSM params) ────────────────────────
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2" {
  name               = "${var.app_name}-${var.environment}-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json

  tags = { Name = "${var.app_name}-${var.environment}-ec2-role" }
}

# Managed policy: Session Manager (no need to open SSH port for remote access)
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Inline policy: read only the specific SSM parameters this app needs
data "aws_iam_policy_document" "ssm_params" {
  statement {
    effect  = "Allow"
    actions = ["ssm:GetParameter", "ssm:GetParameters"]
    resources = [
      aws_ssm_parameter.db_password.arn,
      aws_ssm_parameter.secret_key.arn,
    ]
  }
}

resource "aws_iam_role_policy" "ssm_params" {
  name   = "ssm-params-read"
  role   = aws_iam_role.ec2.id
  policy = data.aws_iam_policy_document.ssm_params.json
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${var.app_name}-${var.environment}-ec2-profile"
  role = aws_iam_role.ec2.name
}

# ── RDS ───────────────────────────────────────────────────────────────────────
module "rds" {
  source = "../../modules/rds"

  app_name             = var.app_name
  environment          = var.environment
  private_subnet_ids   = module.vpc.private_subnet_ids
  rds_sg_id            = module.security_groups.rds_sg_id
  db_name              = var.db_name
  db_username          = var.db_username
  db_password_ssm_path = aws_ssm_parameter.db_password.name
  db_instance_class    = var.db_instance_class

  depends_on = [aws_ssm_parameter.db_password]
}

# ── EC2 ───────────────────────────────────────────────────────────────────────
module "ec2" {
  source = "../../modules/ec2"

  app_name             = var.app_name
  environment          = var.environment
  subnet_id            = module.vpc.public_subnet_ids[0]
  ec2_sg_id            = module.security_groups.ec2_sg_id
  instance_type        = var.instance_type
  key_name             = var.key_name
  iam_instance_profile = aws_iam_instance_profile.ec2.name

  # Database connection (points to RDS)
  db_host              = module.rds.db_host
  db_port              = tostring(module.rds.db_port)
  db_name              = var.db_name
  db_username          = var.db_username
  db_password_ssm_path = aws_ssm_parameter.db_password.name
  secret_key_ssm_path  = aws_ssm_parameter.secret_key.name

  # Docker images
  ghcr_owner     = var.ghcr_owner
  backend_image  = local.backend_image
  frontend_image = local.frontend_image
  image_tag      = var.image_tag

  aws_region = var.aws_region
}

# ── ALB ───────────────────────────────────────────────────────────────────────
module "alb" {
  source = "../../modules/alb"

  app_name         = var.app_name
  environment      = var.environment
  vpc_id           = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  alb_sg_id        = module.security_groups.alb_sg_id
  ec2_instance_id  = module.ec2.instance_id
}
