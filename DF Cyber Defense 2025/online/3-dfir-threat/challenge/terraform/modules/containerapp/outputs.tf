output "backend_api_url" {
  value = "https://${azurerm_container_app.web.latest_revision_fqdn}"
}

output "environment_id" {
  description = "ID of the Container App Environment"
  value       = azurerm_container_app_environment.env.id
}