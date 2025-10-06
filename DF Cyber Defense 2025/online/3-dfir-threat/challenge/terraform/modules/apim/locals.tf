locals {
  apim_name = var.apim_name != null ? var.apim_name : "${var.project_name}-apim"
  api_name  = "${var.project_name}-api"
}