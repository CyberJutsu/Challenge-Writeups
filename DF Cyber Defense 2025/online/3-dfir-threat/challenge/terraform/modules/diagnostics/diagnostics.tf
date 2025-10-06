resource "azurerm_monitor_diagnostic_setting" "acr_diagnostics" {
  name                       = "acr-diagnostics"
  target_resource_id         = var.acr_id
  log_analytics_workspace_id = var.workspace_id

  enabled_log {
    category = "ContainerRegistryRepositoryEvents"
  }

  enabled_log {
    category = "ContainerRegistryLoginEvents"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "azurerm_monitor_diagnostic_setting" "containerenv_diagnostics" {
  name                           = "containerenv-diagnostics"
  target_resource_id             = var.container_env_id
  log_analytics_workspace_id     = var.workspace_id
  log_analytics_destination_type = "Dedicated"

  enabled_log {
    category = "ContainerAppSystemLogs"
  }

  enabled_log {
    category = "ContainerAppConsoleLogs"
  }
}

resource "azurerm_monitor_diagnostic_setting" "storage_blob_diagnostics" {
  name                       = "storage-blob-diagnostics"
  target_resource_id         = "${var.storage_account_id}/blobServices/default"
  log_analytics_workspace_id = var.workspace_id

  enabled_log {
    category = "StorageRead"
  }

  enabled_log {
    category = "StorageWrite"
  }

  enabled_log {
    category = "StorageDelete"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "azurerm_monitor_diagnostic_setting" "app_insights_diagnostics" {
  name                       = "appinsights-diagnostics"
  target_resource_id         = var.app_insights_id
  log_analytics_workspace_id = var.workspace_id

  enabled_log {
    category = "AppRequests"
  }

  enabled_log {
    category = "AppTraces"
  }

  enabled_log {
    category = "AppExceptions"
  }

  enabled_log {
    category = "AppMetrics"
  }

  enabled_log {
    category = "AppEvents"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "azurerm_monitor_diagnostic_setting" "apim_diagnostics" {
  name                       = "apim-diagnostics"
  target_resource_id         = var.apim_id
  log_analytics_workspace_id = var.workspace_id

  enabled_log {
    category = "GatewayLogs"
  }

  enabled_log {
    category = "WebSocketConnectionLogs"
  }

  enabled_log {
    category = "DeveloperPortalAuditLogs"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}