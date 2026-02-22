variable "app_name"          { type = string }
variable "environment"        { type = string }
variable "vpc_id"             { type = string }
variable "public_subnet_ids"  { type = list(string) }
variable "alb_sg_id"          { type = string }
variable "ec2_instance_id"    { type = string }

variable "health_check_path" {
  description = "Path used by ALB target group health checks (nginx proxies to /health on backend)"
  type        = string
  default     = "/health"
}

variable "tags" {
  type    = map(string)
  default = {}
}
