output "instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = azurerm_application_insights.app_insights.instrumentation_key
  sensitive   = true
}

output "app_id" {
  description = "Application Insights application ID"
  value       = azurerm_application_insights.app_insights.app_id
}

output "connection_string" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.app_insights.connection_string
  sensitive   = true
}

output "id" {
  description = "ID of the Application Insights component"
  value       = azurerm_application_insights.app_insights.id
}

output "name" {
  description = "Name of the Application Insights component"
  value       = azurerm_application_insights.app_insights.name
}