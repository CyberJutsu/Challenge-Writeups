resource "azurerm_container_app_environment" "env" {
  name                = "${var.project_name}-env"
  location            = var.location
  resource_group_name = var.resource_group_name
}
