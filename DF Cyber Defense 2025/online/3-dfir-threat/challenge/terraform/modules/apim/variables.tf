variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for the resources"
  type        = string
}

variable "project_name" {
  description = "Name of the project for resource naming"
  type        = string
}

variable "apim_name" {
  description = "Name of the API Management service"
  type        = string
  default     = null
}

variable "publisher_email" {
  description = "Email address of the publisher"
  type        = string
  default     = "admin@example.com"
}

variable "publisher_name" {
  description = "Name of the publisher"
  type        = string
  default     = "QRWeb Admin"
}

variable "app_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  type        = string
  sensitive   = true
}

variable "app_insights_id" {
  description = "Application Insights resource ID"
  type        = string
}

variable "container_app_url" {
  description = "URL of the container app backend"
  type        = string
}

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}