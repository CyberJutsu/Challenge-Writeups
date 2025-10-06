resource "azurerm_application_insights" "app_insights" {
  name                = local.app_insights_name
  location            = var.location
  resource_group_name = var.resource_group_name
  application_type    = "web"
  workspace_id        = var.workspace_id

  tags = var.tags
}