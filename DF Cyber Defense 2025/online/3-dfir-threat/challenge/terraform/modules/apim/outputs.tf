output "apim_id" {
  description = "ID of the API Management service"
  value       = azurerm_api_management.apim.id
}

output "apim_name" {
  description = "Name of the API Management service"
  value       = azurerm_api_management.apim.name
}

output "gateway_url" {
  description = "Gateway URL of the API Management service"
  value       = azurerm_api_management.apim.gateway_url
}

output "api_id" {
  description = "ID of the API"
  value       = azurerm_api_management_api.api.id
}

output "api_name" {
  description = "Name of the API"
  value       = azurerm_api_management_api.api.name
}