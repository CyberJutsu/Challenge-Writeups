resource "random_string" "acr_suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "azurerm_container_registry" "acr" {
  name                = "acr${var.project_name}${random_string.acr_suffix.result}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = false
}


# resource "null_resource" "build_push" {
#   triggers = {
#     hash = filesha256("${path.module}/${local.acr.docker_context_path}/Dockerfile")
#     tag  = local.acr.image_tag
#   }

#   provisioner "local-exec" {
#     command = <<EOT
#       set -e
#       az acr login -n ${azurerm_container_registry.acr.name}
#       docker build -t ${azurerm_container_registry.acr.login_server}/${local.acr.image_name}:${local.acr.image_tag} ${path.module}/${local.acr.docker_context_path}
#       docker push ${azurerm_container_registry.acr.login_server}/${local.acr.image_name}:${local.acr.image_tag}
#     EOT
#   }

#   depends_on = [
#     azurerm_container_registry.acr,
#     azurerm_resource_group.resource_group
#   ]
# }