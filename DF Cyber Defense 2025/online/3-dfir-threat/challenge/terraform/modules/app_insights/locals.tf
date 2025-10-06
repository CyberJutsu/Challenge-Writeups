locals {
  app_insights_name = var.app_insights_name != null ? var.app_insights_name : "${var.project_name}-insights"
}