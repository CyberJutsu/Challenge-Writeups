locals {
  workspace_name = var.workspace_name != null ? var.workspace_name : "${var.project_name}-logs"
}