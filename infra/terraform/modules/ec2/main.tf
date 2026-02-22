# ──────────────────────────────────────────────────────────────────────────────
# EC2 — Amazon Linux 2023, runs Docker Compose (backend + frontend)
#
# Secrets (DB password, JWT key) are fetched from SSM at boot — never stored
# in user_data or Terraform state in plaintext.
# ──────────────────────────────────────────────────────────────────────────────

# Latest Amazon Linux 2023 AMI (x86_64)
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [var.ec2_sg_id]
  key_name               = var.key_name
  iam_instance_profile   = var.iam_instance_profile

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    aws_region           = var.aws_region
    app_name             = var.app_name
    environment          = var.environment
    db_host              = var.db_host
    db_port              = var.db_port
    db_name              = var.db_name
    db_username          = var.db_username
    db_password_ssm_path = var.db_password_ssm_path
    secret_key_ssm_path  = var.secret_key_ssm_path
    backend_image        = var.backend_image
    frontend_image       = var.frontend_image
    image_tag            = var.image_tag
    ghcr_owner           = var.ghcr_owner
  })

  # Re-run user_data when any image tag or secret path changes
  user_data_replace_on_change = false

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    delete_on_termination = true
    encrypted             = true
  }

  metadata_options {
    # IMDSv2 only — prevents SSRF-based metadata exfiltration
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-app"
  })
}
