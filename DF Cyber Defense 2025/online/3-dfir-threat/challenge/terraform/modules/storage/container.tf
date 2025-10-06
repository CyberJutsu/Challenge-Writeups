resource "azurerm_storage_container" "qrcodes" {
  name                  = "qrcodes"
  storage_account_name  = azurerm_storage_account.storage_account.name
  container_access_type = "private"

  depends_on = [
    azurerm_storage_account.storage_account
  ]
}

resource "azurerm_storage_container" "internal" {
  name                  = "internal"
  storage_account_name  = azurerm_storage_account.storage_account.name
  container_access_type = "private"

  depends_on = [
    azurerm_storage_account.storage_account
  ]
}
