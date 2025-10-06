variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "workspace_id" {
  description = "ID of the Log Analytics workspace"
  type        = string
}

variable "acr_id" {
  description = "ID of the Azure Container Registry"
  type        = string
}

variable "storage_account_id" {
  description = "ID of the Storage Account"
  type        = string
}

variable "container_env_id" {
  description = "ID of the Container App Environment"
  type        = string
}

variable "project_name" {
  description = "Name of the project for resource naming"
  type        = string
}

variable "app_insights_id" {
  description = "ID of the Application Insights component"
  type        = string
}

variable "apim_id" {
  description = "ID of the API Management service"
  type        = string
}