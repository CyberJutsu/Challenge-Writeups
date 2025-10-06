output "resource_group_name" {
  value = azurerm_resource_group.resource_group.name
}

output "resource_group_location" {
  value = azurerm_resource_group.resource_group.location
}

output "acr_login_server" {
  value = module.acr_01.login_server
}

output "storage_account_name" {
  value = module.storage_01.storage_account_name
}

output "storage_account_primary_access_key" {
  value     = module.storage_01.storage_account_primary_access_key
  sensitive = true
}

output "backend_api_url" {
  value = module.containerapp_01.backend_api_url
}

output "log_analytics_workspace_id" {
  description = "ID of the Log Analytics workspace"
  value       = module.log_analytics_01.workspace_id
}

output "application_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = module.app_insights_01.instrumentation_key
  sensitive   = true
}

output "apim_gateway_url" {
  description = "APIM Gateway URL"
  value       = module.apim_01.gateway_url
}

output "public_ip_address" {
  description = "Public IP address for Application Gateway"
  value       = module.networking_01.public_ip_address
}