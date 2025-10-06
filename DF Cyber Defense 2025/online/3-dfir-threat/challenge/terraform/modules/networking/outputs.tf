output "vnet_id" {
  description = "ID of the virtual network"
  value       = azurerm_virtual_network.vnet.id
}

output "vnet_name" {
  description = "Name of the virtual network"
  value       = azurerm_virtual_network.vnet.name
}

output "subnet_id" {
  description = "ID of the default subnet"
  value       = azurerm_subnet.default.id
}

output "subnet_name" {
  description = "Name of the default subnet"
  value       = azurerm_subnet.default.name
}

output "public_ip_id" {
  description = "ID of the public IP"
  value       = azurerm_public_ip.appgw_pip.id
}

output "public_ip_address" {
  description = "IP address of the public IP"
  value       = azurerm_public_ip.appgw_pip.ip_address
}