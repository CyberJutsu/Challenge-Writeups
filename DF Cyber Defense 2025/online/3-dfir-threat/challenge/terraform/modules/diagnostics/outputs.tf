output "acr_diagnostic_setting_id" {
  description = "ID of the ACR diagnostic setting"
  value       = azurerm_monitor_diagnostic_setting.acr_diagnostics.id
}

output "container_env_diagnostic_setting_id" {
  description = "ID of the Container App Environment diagnostic setting"
  value       = azurerm_monitor_diagnostic_setting.containerenv_diagnostics.id
}

output "storage_blob_diagnostic_setting_id" {
  description = "ID of the Storage Blob diagnostic setting"
  value       = azurerm_monitor_diagnostic_setting.storage_blob_diagnostics.id
}

output "app_insights_diagnostic_setting_id" {
  description = "ID of the Application Insights diagnostic setting"
  value       = azurerm_monitor_diagnostic_setting.app_insights_diagnostics.id
}

output "apim_diagnostic_setting_id" {
  description = "ID of the APIM diagnostic setting"
  value       = azurerm_monitor_diagnostic_setting.apim_diagnostics.id
}