resource "azurerm_resource_group" "resource_group" {
  name     = local.resource_group.name
  location = local.resource_group.location
}

module "acr_01" {
  source = "./modules/acr"

  resource_group_name = azurerm_resource_group.resource_group.name
  location            = azurerm_resource_group.resource_group.location
  project_name        = var.project_name
}

module "storage_01" {
  source = "./modules/storage"

  resource_group_name = azurerm_resource_group.resource_group.name
  location            = azurerm_resource_group.resource_group.location
  project_name        = var.project_name
}

module "networking_01" {
  source = "./modules/networking"

  resource_group_name = azurerm_resource_group.resource_group.name
  location            = azurerm_resource_group.resource_group.location
  project_name        = var.project_name
}

module "log_analytics_01" {
  source = "./modules/log_analytics"

  resource_group_name = azurerm_resource_group.resource_group.name
  location            = azurerm_resource_group.resource_group.location
  project_name        = var.project_name
}

module "app_insights_01" {
  source = "./modules/app_insights"

  resource_group_name = azurerm_resource_group.resource_group.name
  location            = azurerm_resource_group.resource_group.location
  project_name        = var.project_name
  workspace_id        = module.log_analytics_01.workspace_id
}

module "containerapp_01" {
  source = "./modules/containerapp"

  resource_group_name  = azurerm_resource_group.resource_group.name
  location             = azurerm_resource_group.resource_group.location
  project_name         = var.project_name
  acr_login_server     = module.acr_01.login_server
  acr_id               = module.acr_01.id
  storage_account_name = module.storage_01.storage_account_name
  storage_account_id   = module.storage_01.storage_account_id
}

module "apim_01" {
  source = "./modules/apim"

  resource_group_name              = azurerm_resource_group.resource_group.name
  location                         = azurerm_resource_group.resource_group.location
  project_name                     = var.project_name
  publisher_email                  = var.publisher_email
  publisher_name                   = var.publisher_name
  app_insights_instrumentation_key = module.app_insights_01.instrumentation_key
  app_insights_id                  = module.app_insights_01.id
  container_app_url                = module.containerapp_01.backend_api_url
  subscription_id                  = var.subscription_id
}

module "diagnostics_01" {
  source = "./modules/diagnostics"

  resource_group_name = azurerm_resource_group.resource_group.name
  workspace_id        = module.log_analytics_01.workspace_id
  acr_id              = module.acr_01.id
  storage_account_id  = module.storage_01.storage_account_id
  container_env_id    = module.containerapp_01.environment_id
  app_insights_id     = module.app_insights_01.id
  apim_id             = module.apim_01.apim_id
  project_name        = var.project_name
}
