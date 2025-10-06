resource "azurerm_container_app" "web" {
  name                         = "${var.project_name}-web"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.env.id
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.identity.id]
  }

  template {
    container {
      name   = "${var.project_name}-web"
      image  = "${var.acr_login_server}/qrzure:latest"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = var.storage_account_name
      }

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.identity.client_id
      }

      env {
        name  = "AZURE_TENANT_ID"
        value = data.azurerm_client_config.current.tenant_id
      }
    }
    min_replicas = 1
    max_replicas = 2
  }

  ingress {
    allow_insecure_connections = false
    external_enabled           = true
    transport                  = "http"
    target_port                = 3000
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  registry {
    server   = var.acr_login_server
    identity = azurerm_user_assigned_identity.identity.id
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_role_assignment.storage_blob_contributor,
    null_resource.delete_existing_container_app
  ]
}

resource "null_resource" "delete_existing_container_app" {
  provisioner "local-exec" {
    command = "az containerapp delete --name ${var.project_name}-web --resource-group ${var.resource_group_name} --yes || echo 'Container app not found or already deleted'"
  }
}
