variable "project_name" {
  type        = string
  description = "Project name used for resource naming"
  default     = "qrweb"
}

variable "resource_group" {
  type        = string
  description = "Resource group name"
  default     = "qrzure"
}

variable "location" {
  type        = string
  description = "Azure region for resources"
  default     = "Southeast Asia"
}

variable "subscription_id" {
  type        = string
  description = "Azure subscription ID"
  default     = "1f1b2402-8543-4100-9627-59fa5ce96944"
}

variable "publisher_email" {
  type        = string
  description = "Email address for APIM publisher"
  default     = "admin@zure.co"
}

variable "publisher_name" {
  type        = string
  description = "Name for APIM publisher"
  default     = "Admin"
}

