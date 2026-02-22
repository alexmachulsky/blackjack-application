output "instance_id" {
  value = aws_instance.app.id
}

output "public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.app.public_ip
}

output "public_dns" {
  value = aws_instance.app.public_dns
}
