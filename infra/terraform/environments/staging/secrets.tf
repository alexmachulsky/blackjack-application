variable "db_password" {
  description = "Database master password — pass via TF_VAR_db_password env var or CI secret"
  type        = string
  sensitive   = true
}

variable "app_secret_key" {
  description = "JWT secret key — pass via TF_VAR_app_secret_key env var or CI secret"
  type        = string
  sensitive   = true
}
