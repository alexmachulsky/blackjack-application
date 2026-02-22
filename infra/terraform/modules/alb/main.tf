# ──────────────────────────────────────────────────────────────────────────────
# Application Load Balancer
#
# Internet-facing ALB → Target Group → EC2 (port 80, nginx frontend)
# /health is proxied by nginx to backend → used for ALB health checks
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_lb" "this" {
  name               = "${var.app_name}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_sg_id]
  subnets            = var.public_subnet_ids

  # Prevent accidental deletion in production
  enable_deletion_protection = false

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-alb"
  })
}

resource "aws_lb_target_group" "app" {
  name        = "${var.app_name}-${var.environment}-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "instance"

  health_check {
    enabled             = true
    path                = var.health_check_path
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-tg"
  })
}

resource "aws_lb_target_group_attachment" "app" {
  target_group_arn = aws_lb_target_group.app.arn
  target_id        = var.ec2_instance_id
  port             = 80
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
