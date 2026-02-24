output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = module.eks.cluster_endpoint
}

output "kubeconfig_command" {
  description = "Run this to configure kubectl"
  value       = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.aws_region}"
}

output "ssm_db_password_path" {
  description = "SSM path for the DB password"
  value       = aws_ssm_parameter.db_password.name
}

output "ssm_secret_key_path" {
  description = "SSM path for the JWT secret key"
  value       = aws_ssm_parameter.secret_key.name
}

output "deploy_command" {
  description = "Run this to deploy the application to the cluster"
  value       = "cd ../../../k8s && ./deploy.sh"
}
