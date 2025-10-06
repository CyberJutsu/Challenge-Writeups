resource "azurerm_api_management" "apim" {
  name                = local.apim_name
  location            = var.location
  resource_group_name = var.resource_group_name
  publisher_name      = var.publisher_name
  publisher_email     = var.publisher_email
  sku_name           = "Consumption_0"

  tags = var.tags
}

resource "azurerm_api_management_api" "api" {
  name                = local.api_name
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.apim.name
  revision            = "1"
  display_name        = "QR Web API"
  path                = ""
  protocols           = ["https"]
  service_url         = var.container_app_url
  subscription_required = false

  depends_on = [azurerm_api_management.apim]
}

resource "azurerm_api_management_logger" "appinsights" {
  name                = "appinsights"
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  resource_id         = var.app_insights_id

  application_insights {
    instrumentation_key = var.app_insights_instrumentation_key
  }

  depends_on = [azurerm_api_management.apim]
}

resource "azurerm_api_management_api_operation" "get_root" {
  operation_id        = "get-root"
  api_name           = azurerm_api_management_api.api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name       = "Get Root"
  method             = "GET"
  url_template       = "/"

  description = "Proxy GET requests to root path"

  response {
    status_code = 200
    description = "Success"
    representation {
      content_type = "text/html"
    }
  }

  depends_on = [azurerm_api_management_api.api]
}

resource "azurerm_api_management_api_operation" "get_all" {
  operation_id        = "get-all"
  api_name           = azurerm_api_management_api.api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name       = "Get All Paths"
  method             = "GET"
  url_template       = "/*"

  description = "Proxy all GET requests"

  response {
    status_code = 200
    description = "Success"
  }

  depends_on = [azurerm_api_management_api.api]
}

resource "azurerm_api_management_api_operation" "post_all" {
  operation_id        = "post-all"
  api_name           = azurerm_api_management_api.api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name       = "Post All Paths"
  method             = "POST"
  url_template       = "/*"

  description = "Proxy all POST requests"

  response {
    status_code = 200
    description = "Success"
  }

  depends_on = [azurerm_api_management_api.api]
}

resource "azurerm_api_management_api_diagnostic" "api_diagnostics" {
  identifier               = "applicationinsights"
  resource_group_name     = var.resource_group_name
  api_management_name     = azurerm_api_management.apim.name
  api_name                = azurerm_api_management_api.api.name
  api_management_logger_id = azurerm_api_management_logger.appinsights.id

  sampling_percentage       = 100.0
  always_log_errors        = true
  log_client_ip            = true
  verbosity                = "verbose"
  http_correlation_protocol = "W3C"

  frontend_request {
    body_bytes = 8192
    headers_to_log = []
  }

  frontend_response {
    body_bytes = 8192
    headers_to_log = []
  }

  backend_request {
    body_bytes = 8192
    headers_to_log = []
  }

  backend_response {
    body_bytes = 8192
    headers_to_log = []
  }

  depends_on = [azurerm_api_management_api.api, azurerm_api_management_logger.appinsights]
}