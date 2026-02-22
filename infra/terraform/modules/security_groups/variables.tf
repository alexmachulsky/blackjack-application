variable "app_name" { type = string }
variable "environment" { type = string }
variable "vpc_id" { type = string }

variable "admin_cidr" {
  description = "CIDR allowed to SSH into the EC2 instance (e.g. your office IP)"
  type        = string
  default     = "0.0.0.0/0" # narrow this in production
}

variable "tags" {
  type    = map(string)
  default = {}
}
