output "alb_dns_name" {
  description = "DNS name of the ALB — use this as the application URL"
  value       = aws_lb.this.dns_name
}

output "alb_zone_id" {
  description = "Route 53 hosted zone ID for the ALB (for alias records)"
  value       = aws_lb.this.zone_id
}

output "alb_arn" {
  value = aws_lb.this.arn
}

output "target_group_arn" {
  value = aws_lb_target_group.app.arn
}
