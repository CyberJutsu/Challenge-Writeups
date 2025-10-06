resource "azurerm_user_assigned_identity" "identity" {
  name                = "${var.project_name}-web-identity"
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.identity.principal_id

  depends_on = [
    azurerm_user_assigned_identity.identity
  ]
}

resource "azurerm_role_assignment" "storage_blob_contributor" {
  scope                = var.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.identity.principal_id

  depends_on = [
    azurerm_user_assigned_identity.identity
  ]
}
