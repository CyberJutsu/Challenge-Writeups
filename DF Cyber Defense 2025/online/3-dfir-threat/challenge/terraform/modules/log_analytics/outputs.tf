output "workspace_id" {
  description = "ID of the Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.workspace.id
}

output "workspace_name" {
  description = "Name of the Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.workspace.name
}

output "primary_shared_key" {
  description = "Primary shared key for the Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.workspace.primary_shared_key
  sensitive   = true
}

output "workspace_data" {
  description = "Log Analytics workspace data for other modules"
  value = {
    id   = azurerm_log_analytics_workspace.workspace.id
    name = azurerm_log_analytics_workspace.workspace.name
  }
}