output "alb_dns_name" {
  description = "Application URL — open this in your browser"
  value       = "http://${module.alb.alb_dns_name}"
}

output "ec2_public_ip" {
  description = "EC2 instance public IP (for SSH: ssh ec2-user@<ip>)"
  value       = module.ec2.public_ip
}

output "rds_endpoint" {
  description = "RDS endpoint (host:port)"
  value       = module.rds.db_endpoint
}

output "ssm_db_password_path" {
  description = "SSM path for the DB password"
  value       = aws_ssm_parameter.db_password.name
}

output "ssm_secret_key_path" {
  description = "SSM path for the JWT secret key"
  value       = aws_ssm_parameter.secret_key.name
}
