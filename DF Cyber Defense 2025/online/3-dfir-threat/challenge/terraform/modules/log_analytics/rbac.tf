resource "azurerm_role_definition" "dfir_analyst" {
  name     = "${var.project_name}-dfir-analyst"
  scope    = var.workspace_id

  description = "DFIR CTF Challenge - Log Analytics read-only access"

  permissions {
    actions = [
      "Microsoft.OperationalInsights/workspaces/read",
      "Microsoft.OperationalInsights/workspaces/query/read",
      "Microsoft.OperationalInsights/workspaces/search/read"
    ]
    data_actions = [
      "Microsoft.OperationalInsights/workspaces/query/*/read"
    ]
    not_actions = []
    not_data_actions = []
  }

  assignable_scopes = [
    var.workspace_id
  ]
}

# Create service principal for players
resource "azuread_application" "dfir_player" {
  display_name = "${var.project_name}-dfir-player"

  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000" # Microsoft Graph

    resource_access {
      id   = "e1fe6dd8-ba31-4d61-89e7-88639da4683d" # User.Read
      type = "Scope"
    }
  }
}

resource "azuread_service_principal" "dfir_player" {
  application_id = azuread_application.dfir_player.application_id
}

resource "azuread_application_password" "dfir_player" {
  application_object_id = azuread_application.dfir_player.object_id
  description           = "DFIR CTF Challenge access"
  end_date_relative     = "8760h" # 1 year
}

# Assign the custom role to service principal
resource "azurerm_role_assignment" "dfir_player" {
  scope              = var.workspace_id
  role_definition_id = azurerm_role_definition.dfir_analyst.role_definition_resource_id
  principal_id       = azuread_service_principal.dfir_player.object_id
}